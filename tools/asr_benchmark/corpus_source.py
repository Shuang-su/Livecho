"""Strictly in-memory 60-script speech synthesis (Swift AVSpeechSynthesizer + FFmpeg) and replay."""

from __future__ import annotations

import asyncio
import atexit
import json
import struct
import subprocess
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import suppress
from dataclasses import dataclass
from threading import Lock
from typing import Any

from .contracts import NS, Corpus, Script
from .mlx_adapter import estimate_audio_bearing_bytes
from .pass_coordinator import PreparedCall, ReplayRequest, ReplaySource, SegmentSpan
from .runner import PassPlan
from .runtime import Allocation, BlockedEvidence, Budget, MemoryInput

SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2
BYTES_PER_SECOND = SAMPLE_RATE * BYTES_PER_SAMPLE
TICK_NS = 250_000_000
SILENCE_BYTES_PER_SEC = BYTES_PER_SECOND

VOICE_BY_SPEAKER: dict[str, tuple[str, float]] = {
    "speaker-linfei": ("com.apple.siri.natural.Linfei", 0.24),
    "speaker-tingting": ("com.apple.voice.compact.zh-CN.Tingting", 0.37),
    "speaker-meijia": ("com.apple.voice.super-compact.zh-TW.Meijia", 0.36),
}

_SWIFT_DAEMON = r"""
import Foundation
import AVFoundation

let synth = AVSpeechSynthesizer()
let out = FileHandle.standardOutput

func writeAll(_ data: Data) {
    out.write(data)
}

while let line = readLine(strippingNewline: true) {
    if line == "__QUIT__" { break }
    guard let jsonData = line.data(using: .utf8),
          let obj = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any],
          let voiceId = obj["voice"] as? String,
          let rateNum = obj["rate"] as? NSNumber,
          let text = obj["text"] as? String else {
        var zero: UInt32 = 0
        writeAll(Data(bytes: &zero, count: 4))
        writeAll(Data(bytes: &zero, count: 4))
        continue
    }

    let utt = AVSpeechUtterance(string: text)
    utt.voice = AVSpeechSynthesisVoice(identifier: voiceId)
    utt.rate = rateNum.floatValue
    utt.preUtteranceDelay = 0.0
    utt.postUtteranceDelay = 0.0

    var finished = false
    var sampleRate: UInt32 = 0
    var pcmData = Data()

    synth.write(utt) { buffer in
        guard let pcm = buffer as? AVAudioPCMBuffer else { return }
        if pcm.frameLength == 0 {
            finished = true
            return
        }
        if sampleRate == 0 {
            sampleRate = UInt32(pcm.format.sampleRate)
        }
        if let ch = pcm.floatChannelData {
            let nBytes = Int(pcm.frameLength) * MemoryLayout<Float>.size
            pcmData.append(Data(bytes: ch[0], count: nBytes))
        }
    }

    let deadline = Date().addingTimeInterval(20.0)
    while !finished && Date() < deadline {
        RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.005))
    }

    var srLE = sampleRate.littleEndian
    var lenLE = UInt32(pcmData.count).littleEndian
    writeAll(Data(bytes: &srLE, count: 4))
    writeAll(Data(bytes: &lenLE, count: 4))
    if !pcmData.isEmpty {
        writeAll(pcmData)
    }
}
"""


class SwiftFFmpegSynthesizer:
    """Persistent in-RAM Swift AVSpeechSynthesizer + FFmpeg pipe:0->pipe:1 converter."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg") -> None:
        self._ffmpeg_bin = ffmpeg_bin
        self._lock = Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        atexit.register(self.close)

    def _ensure_proc(self) -> subprocess.Popen[bytes]:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = subprocess.Popen(
                ["/usr/bin/swift", "-e", _SWIFT_DAEMON],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
                bufsize=0,
            )
        return self._proc

    @staticmethod
    def _read_exact(stream: Any, count: int) -> bytes:
        buf = bytearray()
        while len(buf) < count:
            chunk = stream.read(count - len(buf))
            if not chunk:
                raise BlockedEvidence("source_synthesis_failed")
            buf.extend(chunk)
        return bytes(buf)

    def synthesize_pcm_s16le(self, voice_id: str, rate: float, text: str) -> bytes:
        """Return 16 kHz mono pcm_s16le bytes strictly in RAM (zero disk writes)."""
        payload = (json.dumps({"voice": voice_id, "rate": rate, "text": text}) + "\n").encode(
            "utf-8"
        )
        with self._lock:
            proc = self._ensure_proc()
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(payload)
            proc.stdin.flush()
            sr = struct.unpack("<I", self._read_exact(proc.stdout, 4))[0]
            byte_len = struct.unpack("<I", self._read_exact(proc.stdout, 4))[0]
            if sr <= 0 or byte_len <= 0:
                raise BlockedEvidence("source_synthesis_failed")
            raw_f32 = self._read_exact(proc.stdout, byte_len)

        conv = subprocess.run(
            [
                self._ffmpeg_bin,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-protocol_whitelist",
                "pipe",
                "-f",
                "f32le",
                "-ar",
                str(sr),
                "-ac",
                "1",
                "-i",
                "pipe:0",
                "-f",
                "s16le",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "1",
                "pipe:1",
            ],
            input=raw_f32,
            capture_output=True,
            check=False,
        )
        del raw_f32
        if conv.returncode != 0 or not conv.stdout:
            raise BlockedEvidence("source_synthesis_failed")
        return conv.stdout

    def close(self) -> None:
        with self._lock:
            proc = self._proc
            self._proc = None
            if proc is not None:
                with suppress(BaseException):
                    if proc.stdin is not None:
                        proc.stdin.write(b"__QUIT__\n")
                        proc.stdin.flush()
                        proc.stdin.close()
                with suppress(BaseException):
                    proc.wait(timeout=1.0)
                if proc.poll() is None:
                    with suppress(BaseException):
                        proc.kill()
                        proc.wait(timeout=1.0)
                if proc.stdout is not None:
                    with suppress(BaseException):
                        proc.stdout.close()


def fit_12s_pcm(raw_pcm: bytes, target_samples: int = 12 * SAMPLE_RATE) -> bytearray:
    """Trim leading/trailing silence in RAM and normalize to exact 12.0s (192,000 samples)."""
    import numpy as np

    samples = np.frombuffer(raw_pcm, dtype=np.int16)
    active = np.flatnonzero(np.abs(samples) >= 120)
    if active.size == 0:
        raise BlockedEvidence("source_synthesis_empty")
    trimmed = samples[int(active[0]) : int(active[-1]) + 1]
    if trimmed.size > target_samples:
        trimmed = trimmed[:target_samples]
    out = np.zeros(target_samples, dtype=np.int16)
    out[: trimmed.size] = trimmed
    return bytearray(out.tobytes())


def add_broadband_noise_10db(clean_pcm: bytearray, script: Script) -> bytearray:
    """Mix deterministic broadband-memory-v1 noise at 10 dB SNR relative to active speech RMS."""
    import numpy as np

    clean = np.frombuffer(clean_pcm, dtype=np.int16).astype(np.float32)
    mask = np.zeros(clean.shape[0], dtype=bool)
    for ct in script.character_times:
        s_idx = (ct.start_ns * SAMPLE_RATE) // NS
        e_idx = min(clean.shape[0], (ct.end_ns * SAMPLE_RATE) // NS)
        if e_idx > s_idx:
            mask[s_idx:e_idx] = True
    active_samples = clean[mask] if np.any(mask) else clean
    speech_rms = float(np.sqrt(np.mean(active_samples * active_samples)))
    if speech_rms <= 0.0:
        raise BlockedEvidence("source_synthesis_empty")
    noise_rms = speech_rms / (10.0 ** (10.0 / 20.0))
    rng = np.random.default_rng(script.noise_seed)
    noise = rng.standard_normal(clean.shape[0], dtype=np.float32) * noise_rms
    noisy = np.clip(np.rint(clean + noise), -32768.0, 32767.0).astype(np.int16)
    del clean, noise, mask, active_samples
    return bytearray(noisy.tobytes())


def _compute_spans(request: ReplayRequest) -> tuple[SegmentSpan, ...]:
    if request.script is None:
        return tuple(
            SegmentSpan(
                start_ns=start,
                end_ns=min(start + request.window_ns, request.duration_ns),
                speech_end_ns=min(start + request.window_ns, request.duration_ns),
            )
            for start in range(0, request.duration_ns, request.window_ns)
        )
    spans: list[SegmentSpan] = []
    pos = 0
    while pos < request.duration_ns:
        limit = min(pos + request.window_ns, request.duration_ns)
        speech_end = pos
        for timing in request.script.character_times:
            if timing.end_ns <= pos:
                continue
            if timing.start_ns >= min(limit, speech_end + 500_000_000):
                break
            speech_end = min(limit, timing.end_ns)
        end_ns = min(limit, speech_end + 500_000_000)
        spans.append(SegmentSpan(start_ns=pos, end_ns=end_ns, speech_end_ns=speech_end))
        pos = end_ns
    return tuple(spans)


@dataclass
class _OwnedSlice:
    buf: bytearray
    view: memoryview | None = None

    def release(self) -> None:
        if self.view is not None:
            with suppress(ValueError):
                self.view.release()
            self.view = None
        if self.buf:
            self.buf[:] = b"\x00" * len(self.buf)
            self.buf.clear()


class InMemoryReplaySource:
    """ReplaySource streaming real-time PTS ticks over strictly RAM-resident PCM."""

    def __init__(
        self,
        request: ReplayRequest,
        budget: Budget,
        origin_ns: int,
        pcm_buffer: bytearray,
        *,
        clock: Callable[[], int] = time.monotonic_ns,
        source_id: str,
    ) -> None:
        self._request = request
        self._budget = budget
        self._origin_ns = origin_ns
        self._clock = clock
        self._pcm = pcm_buffer
        self._pts_ns = 0
        self._retired_bytes = 0
        self._seq = 0
        self._closed = False
        self._slices: list[_OwnedSlice] = []
        self._base_alloc_id = source_id
        self._alloc_id: str | None = f"{source_id}-win-0" if request.script is None else source_id
        self._rolling_bytes = len(self._pcm)
        self.segments = _compute_spans(request)

        # For silence (60s), _pcm only holds <= 1 window (<= 192,000 B) and advances on retire.
        initial_end = (
            min(request.duration_ns, request.window_ns)
            if request.script is None
            else request.duration_ns
        )
        budget.reserve(
            Allocation(
                allocation_id=self._alloc_id,
                start_pts_ns=0,
                end_pts_ns=initial_end,
                audio_bytes=self._rolling_bytes,
                canonical_bytes=self._rolling_bytes,
            ),
            self._release_backing,
        )

    def _release_backing(self) -> None:
        if self._pcm:
            self._pcm[:] = b"\x00" * len(self._pcm)
            self._pcm.clear()

    async def advance(self, deadline_ns: int) -> int | None:
        if self._closed:
            raise BlockedEvidence("source_closed")
        if self._pts_ns >= self._request.duration_ns:
            return None
        next_pts = min(self._pts_ns + TICK_NS, self._request.duration_ns)
        target_ns = self._origin_ns + next_pts
        while True:
            now = self._clock()
            if now >= deadline_ns:
                raise BlockedEvidence("input_stall")
            if now >= target_ns:
                break
            await asyncio.sleep(min(0.01, (target_ns - now) / NS))
        self._pts_ns = next_pts
        return self._pts_ns

    def call_input(self, start_ns: int, end_ns: int) -> PreparedCall:
        if self._closed:
            raise BlockedEvidence("source_closed")
        self._seq += 1
        n_samples = ((end_ns - start_ns) * SAMPLE_RATE) // NS
        canonical_bytes = n_samples * BYTES_PER_SAMPLE
        estimate = estimate_audio_bearing_bytes(canonical_bytes)
        alloc = Allocation(
            allocation_id=f"{self._alloc_id}-call-{self._seq}",
            start_pts_ns=start_ns,
            end_pts_ns=end_ns,
            audio_bytes=estimate.peak_audio_bearing_bytes,
            canonical_bytes=canonical_bytes,
        )
        owned = _OwnedSlice(bytearray())
        self._slices.append(owned)

        def prepare() -> MemoryInput:
            if self._request.script is None:
                owned.buf = bytearray(canonical_bytes)
            else:
                s_byte = ((start_ns * SAMPLE_RATE) // NS) * BYTES_PER_SAMPLE
                e_byte = s_byte + canonical_bytes
                owned.buf = bytearray(self._pcm[s_byte:e_byte])
            owned.view = memoryview(owned.buf)
            return MemoryInput(owned.view, start_ns, end_ns)

        def release() -> None:
            owned.release()

        return PreparedCall(alloc, prepare, release)

    def retire_before(self, pts_ns: int) -> None:
        if self._request.script is None:
            if self._alloc_id is not None:
                self._budget.release(self._alloc_id)
                self._alloc_id = None
            if not self._closed and 0 <= pts_ns < self._request.duration_ns:
                next_end = min(self._request.duration_ns, pts_ns + self._request.window_ns)
                next_id = f"{self._base_alloc_id}-win-{pts_ns}"
                self._budget.reserve(
                    Allocation(
                        allocation_id=next_id,
                        start_pts_ns=pts_ns,
                        end_pts_ns=next_end,
                        audio_bytes=self._rolling_bytes,
                        canonical_bytes=self._rolling_bytes,
                    ),
                    self._release_backing,
                )
                self._alloc_id = next_id
            return
        byte_limit = min(len(self._pcm), ((pts_ns * SAMPLE_RATE) // NS) * BYTES_PER_SAMPLE)
        if byte_limit > self._retired_bytes:
            self._pcm[self._retired_bytes : byte_limit] = b"\x00" * (
                byte_limit - self._retired_bytes
            )
            self._retired_bytes = byte_limit

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for item in self._slices:
            item.release()
        self._slices.clear()
        if self._alloc_id is not None:
            self._budget.release(self._alloc_id)
            self._alloc_id = None


class InMemoryCorpusSourceFactory:
    """SourceFactory synthesizing/mixing each pass strictly in RAM without disk writes."""

    def __init__(
        self,
        corpus: Corpus,
        synthesizer: SwiftFFmpegSynthesizer,
        *,
        plan: PassPlan | None = None,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._sources_by_id = {src.source_id: src for src in corpus.sources}
        self._scripts_by_id = {script.script_id: script for script in corpus.scripts}
        self._synth = synthesizer
        self._clock = clock
        self._counter = 0
        self._sequence: list[tuple[str, Script]] = []
        self._seq_index = 0
        self._prefetch_pool: ThreadPoolExecutor | None = None
        self._next_future: Future[bytearray] | None = None
        if plan is not None:
            self._sequence.append(("clean", self._scripts_by_id[plan.cold_script_id]))
            for condition in plan.conditions:
                for sid in plan.script_ids:
                    self._sequence.append((condition, self._scripts_by_id[sid]))
            self._prefetch_pool = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="tts-prefetch"
            )
            if self._sequence:
                first_cond, first_script = self._sequence[0]
                first_fut = self._prefetch_pool.submit(
                    self._synthesize_buffer, first_cond, first_script
                )
                self._next_future = first_fut
                # Eagerly finish the very first buffer before PassCoordinator captures origin_ns.
                first_fut.result()

    def _synthesize_buffer(self, condition: str, script: Script) -> bytearray:
        src_meta = self._sources_by_id[script.source_id]
        voice_id, rate = VOICE_BY_SPEAKER[src_meta.speaker_id]
        raw = self._synth.synthesize_pcm_s16le(voice_id, rate, script.reference)
        pcm = fit_12s_pcm(raw)
        del raw
        if condition == "noise":
            noisy = add_broadband_noise_10db(pcm, script)
            pcm[:] = b"\x00" * len(pcm)
            pcm = noisy
        return pcm

    def _schedule_prefetch(self) -> None:
        if self._prefetch_pool is None or self._seq_index >= len(self._sequence):
            self._next_future = None
            return
        cond, script = self._sequence[self._seq_index]
        self._next_future = self._prefetch_pool.submit(self._synthesize_buffer, cond, script)

    def close(self) -> None:
        fut = self._next_future
        self._next_future = None
        if fut is not None:
            with suppress(BaseException):
                buf = fut.result()
                buf[:] = b"\x00" * len(buf)
                buf.clear()
        if self._prefetch_pool is not None:
            self._prefetch_pool.shutdown(wait=True)
            self._prefetch_pool = None

    def __call__(self, request: ReplayRequest, budget: Budget, origin_ns: int) -> ReplaySource:
        self._counter += 1
        source_id = f"mem-src-{self._counter}"
        if request.script is None:
            # Warmup or 60s silence: allocate only <= 1 window of zeros (<= 192,000 B).
            pcm = bytearray(min(request.window_ns, request.duration_ns) // NS * BYTES_PER_SECOND)
        elif (
            self._sequence
            and self._seq_index < len(self._sequence)
            and self._sequence[self._seq_index] == (request.condition, request.script)
            and self._next_future is not None
        ):
            pcm = self._next_future.result()
            self._seq_index += 1
            self._schedule_prefetch()
        else:
            pcm = self._synthesize_buffer(request.condition, request.script)
        return InMemoryReplaySource(
            request,
            budget,
            origin_ns,
            pcm,
            clock=self._clock,
            source_id=source_id,
        )
