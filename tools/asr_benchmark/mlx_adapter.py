"""Independent clean-room in-process MLX Qwen3-ASR provider and audio-bearing budget."""

from __future__ import annotations

import io
import json
import math
import time
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Literal

from .cache_reader import VerifiedModelReader
from .contracts import InferenceManifest, Settings
from .runtime import BlockedEvidence, MemoryInput, Prefix, TextUpdate

MAX_AUDIO_BEARING_BYTES = 16_777_216
_CONV_CHUNK_FRAMES = 100
_CONV_WINDOW_INFER = 800
_MAX_KV_POSITIONS = 220
_KV_GROUP_SIZE = 64
_KV_BITS = 8
_KV_BYTES_PER_TOKEN = 60_928  # 28 layers * 2(K+V) * 8 kv_heads * (128*1B + 2*4B scales/biases)
_DEQUANT_SCRATCH_BYTES = 901_120  # 1 layer K+V fp16/bf16 scratch at 220 positions
_CONV_PEAK_BYTES = 3_072_000  # 1 chunk conv2d workspace
_AUDIO_FEATURES_MAX_BYTES = 430_080  # 105 * 2048 * 2 B
_CANONICAL_SAMPLE_RATE = 16_000
_BYTES_PER_SAMPLE = 2

_AUDIO_START_ID = 151669
_AUDIO_END_ID = 151670
_AUDIO_PAD_ID = 151676
_IM_START_ID = 151644
_IM_END_ID = 151645
_ENDOFTEXT_ID = 151643
_ASR_TEXT_TOKEN = "<asr_text>"


@dataclass(frozen=True)
class AllocationEstimate:
    pcm_bytes: int
    mel_bytes: int
    conv_workspace_bytes: int
    audio_features_bytes: int
    kv_cache_bytes: int
    dequant_scratch_bytes: int

    @property
    def peak_audio_bearing_bytes(self) -> int:
        encoder_peak = (
            self.pcm_bytes + self.mel_bytes + self.conv_workspace_bytes + self.audio_features_bytes
        )
        decoder_peak = (
            self.pcm_bytes
            + self.audio_features_bytes
            + self.kv_cache_bytes
            + self.dequant_scratch_bytes
        )
        return max(encoder_peak, decoder_peak)


def estimate_audio_bearing_bytes(
    input_bytes: int, max_kv_positions: int = _MAX_KV_POSITIONS
) -> AllocationEstimate:
    """Upper-bound audio-bearing byte inventory for one segment call."""
    if input_bytes < 0 or max_kv_positions <= 0:
        raise BlockedEvidence("allocation_invalid")
    n_samples = input_bytes // _BYTES_PER_SAMPLE
    n_frames = max(1, 1 + (max(n_samples, 400) + 400 - 400) // 160 - 1)
    mel_bytes = 128 * n_frames * 4
    n_audio_tokens = max(1, ((n_frames + 99) // 100) * 13)
    kv_bytes = max_kv_positions * _KV_BYTES_PER_TOKEN
    estimate = AllocationEstimate(
        pcm_bytes=input_bytes,
        mel_bytes=mel_bytes,
        conv_workspace_bytes=_CONV_PEAK_BYTES,
        audio_features_bytes=min(_AUDIO_FEATURES_MAX_BYTES, n_audio_tokens * 2048 * 2),
        kv_cache_bytes=kv_bytes,
        dequant_scratch_bytes=2 * 8 * max_kv_positions * 128 * 2,
    )
    if estimate.peak_audio_bearing_bytes > MAX_AUDIO_BEARING_BYTES:
        raise BlockedEvidence("budget_exceeded")
    return estimate


def _conv_out_len(length: int) -> int:
    for _ in range(3):
        length = (length - 1) // 2 + 1
    return length


def parse_asr_output(raw_text: str) -> str:
    """Strip Qwen3-ASR language tag prefix; return empty string for silence."""
    if _ASR_TEXT_TOKEN in raw_text:
        prefix, _, transcript = raw_text.partition(_ASR_TEXT_TOKEN)
        if prefix.strip().lower().endswith("none") and not transcript.strip():
            return ""
        return transcript.strip()
    if raw_text.strip().lower() in {"language none", "none"}:
        return ""
    return raw_text.strip()


def _slaney_mel_filterbank(np: Any, sr: int = 16_000, n_fft: int = 400, n_mels: int = 128) -> Any:
    """Compute Slaney-normalized Whisper Mel filterbank matrix of shape [n_freqs, n_mels]."""
    f_min = 0.0
    f_max = sr / 2.0
    f_sp = 200.0 / 3.0
    min_log_hz = 1000.0
    min_log_mel = min_log_hz / f_sp
    logstep = math.log(6.4) / 27.0

    def hz_to_mel(hz: float) -> float:
        if hz >= min_log_hz:
            return min_log_mel + math.log(hz / min_log_hz) / logstep
        return (hz - f_min) / f_sp

    def mel_to_hz(mel: float) -> float:
        if mel >= min_log_mel:
            return min_log_hz * math.exp(logstep * (mel - min_log_mel))
        return f_min + f_sp * mel

    mel_min = hz_to_mel(f_min)
    mel_max = hz_to_mel(f_max)
    mels = np.linspace(mel_min, mel_max, n_mels + 2, dtype=np.float64)
    mel_freqs = np.array([mel_to_hz(float(m)) for m in mels], dtype=np.float64)
    fft_freqs = np.linspace(0.0, f_max, n_fft // 2 + 1, dtype=np.float64)

    fdiff = np.diff(mel_freqs)
    ramps = mel_freqs[:, None] - fft_freqs[None, :]
    weights = np.zeros((n_mels, n_fft // 2 + 1), dtype=np.float64)
    for i in range(n_mels):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0.0, np.minimum(lower, upper))
    enorm = 2.0 / (mel_freqs[2 : n_mels + 2] - mel_freqs[:n_mels])
    weights *= enorm[:, None]
    return weights.T.astype(np.float32)


def compute_whisper_log_mel(pcm_view: memoryview, mel_fb: Any, hann_window: Any) -> Any:
    """Compute [128, T_mel] Whisper log-Mel features strictly in RAM."""
    import numpy as np

    pcm = np.frombuffer(pcm_view, dtype=np.int16).astype(np.float32) / 32768.0
    if pcm.size < 400:
        pcm = np.pad(pcm, (0, 400 - pcm.size))
    padded = np.pad(pcm, (200, 200), mode="reflect")
    del pcm
    n_frames = 1 + (padded.shape[0] - 400) // 160
    strides = (padded.strides[0] * 160, padded.strides[0])
    frames = np.lib.stride_tricks.as_strided(
        padded, shape=(n_frames, 400), strides=strides, writeable=False
    )
    windowed = frames * hann_window
    spec = np.fft.rfft(windowed, axis=-1)
    # Match WhisperFeatureExtractor dropping the final STFT frame.
    if spec.shape[0] > 1:
        spec = spec[:-1]
    power = (spec.real * spec.real + spec.imag * spec.imag).astype(np.float32)
    del padded, frames, windowed, spec
    mel = np.matmul(power, mel_fb).T
    del power
    log_spec = np.log10(np.maximum(mel, 1e-10))
    del mel
    max_val = float(log_spec.max())
    log_spec = np.maximum(log_spec, max_val - 8.0)
    log_spec = (log_spec + 4.0) / 4.0
    return log_spec


def _sinusoid_pos_emb(mx: Any, max_len: int, channels: int, dtype: Any) -> Any:
    import numpy as np

    half = channels // 2
    log_inc = math.log(10000.0) / (half - 1)
    inv_timescales = np.exp(-log_inc * np.arange(half, dtype=np.float32))
    positions = np.arange(max_len, dtype=np.float32)[:, None]
    scaled = positions * inv_timescales[None, :]
    emb = np.concatenate([np.sin(scaled), np.cos(scaled)], axis=1)
    return mx.array(emb, dtype=dtype)


class _Tokenizer:
    """In-memory BPE tokenizer loaded from verified vocab.json + merges.txt + tokenizer_config."""

    def __init__(
        self,
        vocab_bytes: bytes,
        merges_bytes: bytes,
        tokenizer_config_bytes: bytes,
    ) -> None:
        from tokenizers import AddedToken, Tokenizer, decoders, models, pre_tokenizers

        vocab = json.loads(vocab_bytes.decode("utf-8"))
        merges_lines = merges_bytes.decode("utf-8").splitlines()
        merges = [
            tuple(line.split(" ", 1))
            for line in merges_lines
            if line and not line.startswith("#version:") and " " in line
        ]
        bpe = models.BPE(vocab=vocab, merges=merges)
        tok = Tokenizer(bpe)
        tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        tok.decoder = decoders.ByteLevel()

        tok_cfg = json.loads(tokenizer_config_bytes.decode("utf-8"))
        added_decoder = tok_cfg.get("added_tokens_decoder", {})
        special_tokens: list[AddedToken] = []
        regular_tokens: list[AddedToken] = []
        self._id_to_special: dict[int, str] = {}
        for tid_str, meta in sorted(added_decoder.items(), key=lambda kv: int(kv[0])):
            content = str(meta["content"])
            tid = int(tid_str)
            self._id_to_special[tid] = content
            token = AddedToken(
                content,
                single_word=bool(meta.get("single_word", False)),
                lstrip=bool(meta.get("lstrip", False)),
                rstrip=bool(meta.get("rstrip", False)),
                normalized=bool(meta.get("normalized", False)),
                special=bool(meta.get("special", False)),
            )
            if meta.get("special", False):
                special_tokens.append(token)
            else:
                regular_tokens.append(token)
        if regular_tokens:
            tok.add_tokens(regular_tokens)
        if special_tokens:
            tok.add_special_tokens(special_tokens)
        self._tok = tok
        self.newline_id = self.encode_single("\n")
        self.system_id = self.encode_single("system")
        self.user_id = self.encode_single("user")
        self.assistant_id = self.encode_single("assistant")

    def encode_single(self, text: str) -> list[int]:
        ids: list[int] = self._tok.encode(text, add_special_tokens=False).ids
        return ids

    def decode(self, token_ids: list[int]) -> str:
        parts: list[str] = []
        buf: list[int] = []
        for tid in token_ids:
            if tid in self._id_to_special:
                if buf:
                    parts.append(self._tok.decode(buf, skip_special_tokens=False))
                    buf.clear()
                if tid not in {_ENDOFTEXT_ID, _IM_END_ID}:
                    parts.append(self._id_to_special[tid])
            else:
                buf.append(tid)
        if buf:
            parts.append(self._tok.decode(buf, skip_special_tokens=False))
        return "".join(parts)


class _Qwen3ASREngine:
    """Pure MLX forward graph for Qwen3-ASR (0.6B and 1.7B, affine 8-bit group-64)."""

    def __init__(
        self,
        config: dict[str, Any],
        weights: dict[str, Any],
        tokenizer: _Tokenizer,
    ) -> None:
        import importlib

        mx: Any = importlib.import_module("mlx.core")
        nn: Any = importlib.import_module("mlx.nn")

        self.mx = mx
        self.nn = nn
        self.tokenizer = tokenizer
        thinker = config["thinker_config"]
        self.audio_cfg = thinker["audio_config"]
        self.text_cfg = thinker["text_config"]
        self.dtype = mx.bfloat16

        def qlinear(prefix: str, in_dim: int, out_dim: int, *, bias: bool) -> Any:
            layer = nn.QuantizedLinear(
                in_dim,
                out_dim,
                bias=bias,
                group_size=64,
                bits=8,
                mode="affine",
            )
            layer.weight = weights[f"{prefix}.weight"]
            layer.scales = weights[f"{prefix}.scales"]
            layer.biases = weights[f"{prefix}.biases"]
            if bias:
                layer.bias = weights[f"{prefix}.bias"]
            return layer

        def conv2d(prefix: str, in_c: int, out_c: int) -> Any:
            layer = nn.Conv2d(in_c, out_c, kernel_size=3, stride=2, padding=1, bias=True)
            layer.weight = weights[f"{prefix}.weight"]
            layer.bias = weights[f"{prefix}.bias"]
            return layer

        def layernorm(prefix: str, dims: int) -> Any:
            layer = nn.LayerNorm(dims, eps=1e-5)
            layer.weight = weights[f"{prefix}.weight"]
            layer.bias = weights[f"{prefix}.bias"]
            return layer

        def rmsnorm(prefix: str, dims: int, eps: float) -> Any:
            layer = nn.RMSNorm(dims, eps=eps)
            layer.weight = weights[f"{prefix}.weight"]
            return layer

        ac = self.audio_cfg
        d_model = int(ac["d_model"])
        enc_layers = int(ac["encoder_layers"])
        self.enc_heads = int(ac["encoder_attention_heads"])
        self.enc_head_dim = d_model // self.enc_heads
        enc_ffn = int(ac["encoder_ffn_dim"])
        down_c = int(ac["downsample_hidden_size"])
        out_dim = int(ac["output_dim"])
        max_src = int(ac["max_source_positions"])

        self.conv2d1 = conv2d("thinker.audio_tower.conv2d1", 1, down_c)
        self.conv2d2 = conv2d("thinker.audio_tower.conv2d2", down_c, down_c)
        self.conv2d3 = conv2d("thinker.audio_tower.conv2d3", down_c, down_c)
        self.conv_out = qlinear("thinker.audio_tower.conv_out", down_c * 16, d_model, bias=False)
        self.pos_emb = _sinusoid_pos_emb(mx, max_src, d_model, self.dtype)

        self.enc_layers: list[dict[str, Any]] = []
        for idx in range(enc_layers):
            p = f"thinker.audio_tower.layers.{idx}"
            self.enc_layers.append(
                {
                    "attn_ln": layernorm(f"{p}.self_attn_layer_norm", d_model),
                    "q_proj": qlinear(f"{p}.self_attn.q_proj", d_model, d_model, bias=True),
                    "k_proj": qlinear(f"{p}.self_attn.k_proj", d_model, d_model, bias=True),
                    "v_proj": qlinear(f"{p}.self_attn.v_proj", d_model, d_model, bias=True),
                    "out_proj": qlinear(f"{p}.self_attn.out_proj", d_model, d_model, bias=True),
                    "ffn_ln": layernorm(f"{p}.final_layer_norm", d_model),
                    "fc1": qlinear(f"{p}.fc1", d_model, enc_ffn, bias=True),
                    "fc2": qlinear(f"{p}.fc2", enc_ffn, d_model, bias=True),
                }
            )
        self.ln_post = layernorm("thinker.audio_tower.ln_post", d_model)
        self.proj1 = qlinear("thinker.audio_tower.proj1", d_model, d_model, bias=True)
        self.proj2 = qlinear("thinker.audio_tower.proj2", d_model, out_dim, bias=True)

        tc = self.text_cfg
        self.hidden_size = int(tc["hidden_size"])
        self.num_layers = int(tc["num_hidden_layers"])
        self.num_heads = int(tc["num_attention_heads"])
        self.num_kv_heads = int(tc["num_key_value_heads"])
        self.head_dim = int(tc["head_dim"])
        inter_size = int(tc["intermediate_size"])
        vocab_size = int(tc["vocab_size"])
        rms_eps = float(tc["rms_norm_eps"])
        rope_theta = float(tc["rope_theta"])

        self.embed_tokens = nn.QuantizedEmbedding(
            vocab_size, self.hidden_size, group_size=64, bits=8, mode="affine"
        )
        self.embed_tokens.weight = weights["thinker.model.embed_tokens.weight"]
        self.embed_tokens.scales = weights["thinker.model.embed_tokens.scales"]
        self.embed_tokens.biases = weights["thinker.model.embed_tokens.biases"]

        self.rope = nn.RoPE(self.head_dim, traditional=False, base=rope_theta)
        self.dec_layers: list[dict[str, Any]] = []
        for idx in range(self.num_layers):
            p = f"thinker.model.layers.{idx}"
            self.dec_layers.append(
                {
                    "in_ln": rmsnorm(f"{p}.input_layernorm", self.hidden_size, rms_eps),
                    "q_proj": qlinear(
                        f"{p}.self_attn.q_proj",
                        self.hidden_size,
                        self.num_heads * self.head_dim,
                        bias=False,
                    ),
                    "k_proj": qlinear(
                        f"{p}.self_attn.k_proj",
                        self.hidden_size,
                        self.num_kv_heads * self.head_dim,
                        bias=False,
                    ),
                    "v_proj": qlinear(
                        f"{p}.self_attn.v_proj",
                        self.hidden_size,
                        self.num_kv_heads * self.head_dim,
                        bias=False,
                    ),
                    "o_proj": qlinear(
                        f"{p}.self_attn.o_proj",
                        self.num_heads * self.head_dim,
                        self.hidden_size,
                        bias=False,
                    ),
                    "q_norm": rmsnorm(f"{p}.self_attn.q_norm", self.head_dim, rms_eps),
                    "k_norm": rmsnorm(f"{p}.self_attn.k_norm", self.head_dim, rms_eps),
                    "post_ln": rmsnorm(f"{p}.post_attention_layernorm", self.hidden_size, rms_eps),
                    "gate_proj": qlinear(
                        f"{p}.mlp.gate_proj", self.hidden_size, inter_size, bias=False
                    ),
                    "up_proj": qlinear(
                        f"{p}.mlp.up_proj", self.hidden_size, inter_size, bias=False
                    ),
                    "down_proj": qlinear(
                        f"{p}.mlp.down_proj", inter_size, self.hidden_size, bias=False
                    ),
                }
            )
        self.final_norm = rmsnorm("thinker.model.norm", self.hidden_size, rms_eps)
        self.lm_head = qlinear("thinker.lm_head", self.hidden_size, vocab_size, bias=False)

    def encode_audio(self, log_mel_np: Any) -> Any:
        """Encode [128, T_mel] float32 log-Mel into [1, T_audio, hidden_size] (1 chunk/step)."""
        mx = self.mx
        nn = self.nn
        total_frames = int(log_mel_np.shape[1])
        chunk_outputs: list[Any] = []
        for start in range(0, total_frames, _CONV_CHUNK_FRAMES):
            end = min(total_frames, start + _CONV_CHUNK_FRAMES)
            chunk_np = log_mel_np[:, start:end]
            x = mx.array(chunk_np[None, :, :, None], dtype=self.dtype)
            x = nn.gelu(self.conv2d1(x))
            x = nn.gelu(self.conv2d2(x))
            x = nn.gelu(self.conv2d3(x))
            # NHWC [1, 16, W_out, 480] -> channel-major [W_out, 480, 16] -> [W_out, 7680]
            w_out = int(x.shape[2])
            x = x.transpose(0, 2, 3, 1).reshape(w_out, 480 * 16)
            proj = self.conv_out(x) + self.pos_emb[:w_out, :]
            mx.eval(proj)
            chunk_outputs.append(proj)
        audio = mx.concatenate(chunk_outputs, axis=0)[None, :, :]
        del chunk_outputs
        t_audio = int(audio.shape[1])
        block_size = _conv_out_len(_CONV_CHUNK_FRAMES) * (_CONV_WINDOW_INFER // _CONV_CHUNK_FRAMES)
        mask: Any | None = None
        if t_audio > block_size:
            import numpy as np

            block_ids = np.arange(t_audio) // block_size
            same_block = block_ids[:, None] == block_ids[None, :]
            m = np.where(same_block, 0.0, -1e9).astype(np.float32)
            mask = mx.array(m[None, None, :, :], dtype=self.dtype)

        scale = self.enc_head_dim**-0.5
        for layer in self.enc_layers:
            residual = audio
            h = layer["attn_ln"](audio)
            q = layer["q_proj"](h).reshape(1, t_audio, self.enc_heads, self.enc_head_dim)
            k = layer["k_proj"](h).reshape(1, t_audio, self.enc_heads, self.enc_head_dim)
            v = layer["v_proj"](h).reshape(1, t_audio, self.enc_heads, self.enc_head_dim)
            q = q.transpose(0, 2, 1, 3)
            k = k.transpose(0, 2, 1, 3)
            v = v.transpose(0, 2, 1, 3)
            attn = mx.fast.scaled_dot_product_attention(q, k, v, scale=scale, mask=mask)
            attn = attn.transpose(0, 2, 1, 3).reshape(1, t_audio, -1)
            audio = residual + layer["out_proj"](attn)

            residual = audio
            h = layer["ffn_ln"](audio)
            audio = residual + layer["fc2"](nn.gelu(layer["fc1"](h)))
            mx.eval(audio)

        audio = self.ln_post(audio)
        audio = self.proj2(nn.gelu(self.proj1(audio)))
        mx.eval(audio)
        return audio

    def _build_prompt_ids(self, n_audio: int) -> tuple[list[int], int]:
        tok = self.tokenizer
        prefix = [
            _IM_START_ID,
            *tok.system_id,
            *tok.newline_id,
            _IM_END_ID,
            *tok.newline_id,
            _IM_START_ID,
            *tok.user_id,
            *tok.newline_id,
            _AUDIO_START_ID,
        ]
        audio_start_idx = len(prefix)
        suffix = [
            _AUDIO_END_ID,
            _IM_END_ID,
            *tok.newline_id,
            _IM_START_ID,
            *tok.assistant_id,
            *tok.newline_id,
        ]
        return [*prefix, *([_AUDIO_PAD_ID] * n_audio), *suffix], audio_start_idx

    def _decoder_step(
        self,
        embeds: Any,
        cache: list[tuple[tuple[Any, Any, Any], tuple[Any, Any, Any]] | None],
        offset: int,
    ) -> Any:
        mx = self.mx
        nn = self.nn
        seq_len = int(embeds.shape[1])
        scale = self.head_dim**-0.5
        mask = "causal" if seq_len > 1 else None
        x = embeds
        for idx, layer in enumerate(self.dec_layers):
            residual = x
            h = layer["in_ln"](x)
            q = layer["q_proj"](h).reshape(1, seq_len, self.num_heads, self.head_dim)
            k = layer["k_proj"](h).reshape(1, seq_len, self.num_kv_heads, self.head_dim)
            v = layer["v_proj"](h).reshape(1, seq_len, self.num_kv_heads, self.head_dim)
            q = layer["q_norm"](q).transpose(0, 2, 1, 3)
            k = layer["k_norm"](k).transpose(0, 2, 1, 3)
            v = v.transpose(0, 2, 1, 3)
            q = self.rope(q, offset=offset)
            k = self.rope(k, offset=offset)

            kq, ks, kb = mx.quantize(k, group_size=_KV_GROUP_SIZE, bits=_KV_BITS, mode="affine")
            vq, vs, vb = mx.quantize(v, group_size=_KV_GROUP_SIZE, bits=_KV_BITS, mode="affine")
            prev = cache[idx]
            if prev is not None:
                pk, pv = prev
                kq = mx.concatenate([pk[0], kq], axis=2)
                ks = mx.concatenate([pk[1], ks], axis=2)
                kb = mx.concatenate([pk[2], kb], axis=2)
                vq = mx.concatenate([pv[0], vq], axis=2)
                vs = mx.concatenate([pv[1], vs], axis=2)
                vb = mx.concatenate([pv[2], vb], axis=2)
            cache[idx] = ((kq, ks, kb), (vq, vs, vb))

            k_all = mx.dequantize(
                kq,
                ks,
                kb,
                group_size=_KV_GROUP_SIZE,
                bits=_KV_BITS,
                mode="affine",
                dtype=self.dtype,
            )
            v_all = mx.dequantize(
                vq,
                vs,
                vb,
                group_size=_KV_GROUP_SIZE,
                bits=_KV_BITS,
                mode="affine",
                dtype=self.dtype,
            )
            attn = mx.fast.scaled_dot_product_attention(q, k_all, v_all, scale=scale, mask=mask)
            del k_all, v_all
            attn = attn.transpose(0, 2, 1, 3).reshape(1, seq_len, -1)
            x = residual + layer["o_proj"](attn)

            residual = x
            h = layer["post_ln"](x)
            mlp_out = layer["down_proj"](nn.silu(layer["gate_proj"](h)) * layer["up_proj"](h))
            x = residual + mlp_out
        logits = self.lm_head(self.final_norm(x[:, -1:, :]))[:, 0, :]
        mx.eval(logits)
        return logits

    def transcribe_features(self, audio_features: Any, output_limit: int) -> tuple[str, int]:
        mx = self.mx
        n_audio = int(audio_features.shape[1])
        prompt_ids, audio_start_idx = self._build_prompt_ids(n_audio)
        prompt_len = len(prompt_ids)
        if prompt_len >= _MAX_KV_POSITIONS:
            raise BlockedEvidence("budget_exceeded")
        prompt_arr = mx.array([prompt_ids], dtype=mx.int32)
        embeds = self.embed_tokens(prompt_arr)
        before = embeds[:, :audio_start_idx, :]
        after = embeds[:, audio_start_idx + n_audio :, :]
        embeds = mx.concatenate([before, audio_features, after], axis=1)
        mx.eval(embeds)

        cache: list[tuple[tuple[Any, Any, Any], tuple[Any, Any, Any]] | None] = [
            None
        ] * self.num_layers
        generated: list[int] = []
        max_steps = min(output_limit, _MAX_KV_POSITIONS - prompt_len)
        try:
            logits = self._decoder_step(embeds, cache, offset=0)
            offset = prompt_len
            for _ in range(max_steps):
                next_id = int(mx.argmax(logits[0]).item())
                if next_id in {_ENDOFTEXT_ID, _IM_END_ID}:
                    break
                generated.append(next_id)
                if len(generated) >= max_steps:
                    break
                tok_emb = self.embed_tokens(mx.array([[next_id]], dtype=mx.int32))
                logits = self._decoder_step(tok_emb, cache, offset=offset)
                offset += 1
            raw = self.tokenizer.decode(generated)
            return parse_asr_output(raw), len(generated)
        finally:
            cache.clear()
            del embeds


class MLXEagerBackend:
    """EagerModelBackend loading converted MLX Qwen3-ASR assets from FinalModelCache."""

    def __init__(
        self,
        *,
        provider_revision: str,
        dependency_lock_sha256: str,
    ) -> None:
        self.provider_revision = provider_revision
        self.dependency_lock_sha256 = dependency_lock_sha256
        self._unloaded = True
        self.engine: _Qwen3ASREngine | None = None
        self.mel_fb: Any | None = None
        self.hann_window: Any | None = None

    @property
    def unloaded(self) -> bool:
        return self._unloaded

    def initialize(
        self,
        manifest: InferenceManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        if local_files_only is not True or trust_remote_code is not False:
            raise BlockedEvidence("load_backend_mismatch")
        import importlib

        mx: Any = importlib.import_module("mlx.core")
        np: Any = importlib.import_module("numpy")

        config_reader = assets.get("config.json")
        vocab_reader = assets.get("vocab.json")
        merges_reader = assets.get("merges.txt")
        tok_cfg_reader = assets.get("tokenizer_config.json")
        weights_reader = assets.get("model.safetensors")
        if None in (config_reader, vocab_reader, merges_reader, tok_cfg_reader, weights_reader):
            raise BlockedEvidence("cache_final_missing")
        assert config_reader is not None
        assert vocab_reader is not None
        assert merges_reader is not None
        assert tok_cfg_reader is not None
        assert weights_reader is not None

        config = json.loads(config_reader.read_all_verified().decode("utf-8"))
        tokenizer = _Tokenizer(
            vocab_reader.read_all_verified(),
            merges_reader.read_all_verified(),
            tok_cfg_reader.read_all_verified(),
        )
        raw_weights = weights_reader.read_all_verified()
        buf = io.BytesIO(raw_weights)
        del raw_weights
        try:
            loaded_raw = mx.load(buf, format="safetensors")
        finally:
            buf.close()
        weights: dict[str, Any] = dict(loaded_raw)
        values = list(weights.values())
        for start in range(0, len(values), 64):
            mx.eval(*values[start : start + 64])
        mx.synchronize()

        self.engine = _Qwen3ASREngine(config, weights, tokenizer)
        self.mel_fb = _slaney_mel_filterbank(np)
        self.hann_window = np.hanning(401)[:-1].astype(np.float32)
        self._unloaded = False

    def synchronize(self) -> None:
        if self.engine is not None:
            self.engine.mx.synchronize()

    def close(self) -> None:
        self.engine = None
        self.mel_fb = None
        self.hann_window = None
        self._unloaded = True
        with suppress(BaseException):
            import mlx.core as mx

            mx.clear_cache()


class MLXASRProvider:
    """In-process Provider implementing Qwen3-ASR inference with immediate RAM teardown."""

    def __init__(
        self,
        backend: MLXEagerBackend,
        *,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._backend = backend
        self._clock = clock
        self._output_limit = 512
        self._loaded = False

    def load(self, manifest: InferenceManifest, settings: Settings) -> None:
        if self._backend.unloaded or self._backend.engine is None:
            raise BlockedEvidence("load_not_ready")
        self._output_limit = int(settings.output_token_limit)
        self._loaded = True

    def transcribe(self, memory_view: MemoryInput, timing: Prefix) -> TextUpdate:
        if not self._loaded or self._backend.engine is None:
            raise BlockedEvidence("independent_mlx_adapter_unavailable")
        if memory_view.view.nbytes <= 0:
            raise BlockedEvidence("allocation_invalid")
        estimate = estimate_audio_bearing_bytes(memory_view.view.nbytes)
        if estimate.peak_audio_bearing_bytes > MAX_AUDIO_BEARING_BYTES:
            raise BlockedEvidence("budget_exceeded")

        engine = self._backend.engine
        log_mel = compute_whisper_log_mel(
            memory_view.view, self._backend.mel_fb, self._backend.hann_window
        )
        audio_features: Any | None = None
        try:
            audio_features = engine.encode_audio(log_mel)
            del log_mel
            text, tokens = engine.transcribe_features(audio_features, self._output_limit)
            engine.mx.synchronize()
            observed_ns = self._clock()
            return TextUpdate(text=text, observed_ns=observed_ns, output_tokens=tokens)
        finally:
            audio_features = None
            del audio_features
            with suppress(BaseException):
                engine.mx.clear_cache()

    def synchronize(self) -> None:
        self._backend.synchronize()

    def close(self) -> None:
        self._loaded = False
        self._backend.close()
