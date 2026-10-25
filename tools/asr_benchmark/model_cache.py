"""POSIX model-only preparation cache; never used by the audio/provider interfaces.

The CLI registry remains empty. Callers must supply an approved preparation manifest
and feed only its allowlisted model transfer; this module performs no network access.
Private directories and cooperative per-asset locks protect the cache transaction.
This does not claim protection against a malicious host with the operator's privileges.
"""

import fcntl
import hashlib
import os
import stat
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Literal, Self

from pydantic import ValidationError

from .contracts import Asset, PreparationManifest, metadata_digest
from .preparation import TransferCheckpoint
from .runtime import BlockedEvidence

if TYPE_CHECKING:
    from .cache_reader import VerifiedModelReader

Identity = tuple[str, str, str]
Fingerprint = tuple[int, int, int, int, int]


def _fingerprint(value: os.stat_result) -> Fingerprint:
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _private_file(fd: int) -> os.stat_result:
    value = os.fstat(fd)
    if (
        not stat.S_ISREG(value.st_mode)
        or value.st_uid != os.geteuid()
        or value.st_nlink != 1
        or value.st_mode & 0o077
    ):
        raise BlockedEvidence("cache_file_unsafe")
    return value


def _root_fd(root: Path, repository_root: Path, *, create: bool = True) -> int:
    if not root.is_absolute() or ".." in root.parts:
        raise BlockedEvidence("cache_root_unsafe")
    if root.resolve().is_relative_to(repository_root.resolve()):
        raise BlockedEvidence("cache_inside_git")
    current = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(root.parts[1:]):
            # A worktree's .git is a file, so test existence rather than directory type.
            try:
                os.stat(".git", dir_fd=current, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise BlockedEvidence("cache_inside_git")
            if create and index == len(root.parts) - 2:
                with suppress(FileExistsError):
                    os.mkdir(part, mode=0o700, dir_fd=current)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        value = os.fstat(current)
        if value.st_uid != os.geteuid() or value.st_mode & 0o077:
            raise BlockedEvidence("cache_root_unsafe")
        try:
            os.stat(".git", dir_fd=current, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise BlockedEvidence("cache_inside_git")
        return current
    except BaseException:
        os.close(current)
        raise


class ModelOnlyCache:
    def __init__(
        self,
        root: Path,
        repository_root: Path,
        manifest: PreparationManifest,
        mode: Literal["huggingface", "modelscope"],
    ) -> None:
        mirrors = [mirror for mirror in manifest.mirrors if mirror.mode == mode]
        if len(mirrors) != 1:
            raise BlockedEvidence("preparation_not_allowlisted")
        self._preparation_sha256 = metadata_digest(manifest)
        self._assets = {
            (self._preparation_sha256, mirrors[0].revision, asset.sha256): asset
            for asset in manifest.source_assets
        }
        # Two assets can have identical content, but their shared key must not conceal
        # inconsistent lengths. The model cache stores content, never asset path names.
        if any(
            self._assets[(metadata_digest(manifest), mirrors[0].revision, a.sha256)].size != a.size
            for a in manifest.source_assets
        ):
            raise BlockedEvidence("cache_asset_identity")
        self.mode = mode
        try:
            self._directory = _root_fd(root, repository_root)
        except BlockedEvidence:
            raise
        except BaseException:
            raise BlockedEvidence("cache_root_unsafe") from None
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            os.close(self._directory)

    def entry(self, identity: Identity) -> "ModelCacheEntry":
        if self.closed or identity not in self._assets:
            raise BlockedEvidence("cache_identity_denied")
        return ModelCacheEntry(self._directory, identity, self._assets[identity], self.mode)

    def require_preparation(
        self, manifest: PreparationManifest, mode: Literal["huggingface", "modelscope"]
    ) -> None:
        if (
            self.closed
            or mode != self.mode
            or metadata_digest(manifest) != self._preparation_sha256
        ):
            raise BlockedEvidence("cache_identity_denied")

    def open_verified_source(
        self, identity: Identity, cancelled: Callable[[], bool]
    ) -> "VerifiedModelReader":
        from .cache_reader import VerifiedModelReader

        return VerifiedModelReader.from_entry(self.entry(identity), cancelled, owns_entry=True)


class ModelCacheEntry:
    """One locked model transfer. All names are identity-derived and directory-relative."""

    def __init__(
        self,
        directory: int,
        identity: Identity,
        asset: Asset,
        mode: Literal["huggingface", "modelscope"],
    ) -> None:
        self.identity, self.asset, self.mode = identity, asset, mode
        self._directory = os.dup(directory)
        self._lock = self._partial = -1
        self._verified: Fingerprint | None = None
        self._promoted = False
        self.closed = False
        self._key = hashlib.sha256("|".join(identity).encode("ascii")).hexdigest()
        try:
            self._lock = os.open(
                self._name("lock"),
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self._directory,
            )
            _private_file(self._lock)
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BaseException:
            self.close()
            raise BlockedEvidence("cache_lock_unavailable") from None

    def _name(self, suffix: str) -> str:
        return f"{self._key}.{suffix}"

    def _require(self, identity: Identity) -> None:
        if self.closed or identity != self.identity:
            raise BlockedEvidence("cache_identity_denied")

    def _open_partial(self) -> int:
        self._require(self.identity)
        if self._promoted:
            raise BlockedEvidence("cache_already_promoted")
        if self._partial == -1:
            self._partial = os.open(
                self._name("partial"),
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=self._directory,
            )
        _private_file(self._partial)
        return self._partial

    def offset(self) -> int:
        self._require(self.identity)
        try:
            size = os.fstat(self._open_partial()).st_size
            if size > self.asset.size:
                raise BlockedEvidence("cache_length")
            return size
        except BaseException:
            self.invalidate_partial(self.identity)
            raise BlockedEvidence("cache_partial_invalid") from None

    def append_model_chunk(self, chunk: bytes, expected_offset: int) -> None:
        self._require(self.identity)
        if (
            type(chunk) is not bytes
            or not 0 < len(chunk) <= 1024**2
            or type(expected_offset) is not int
            or expected_offset < 0
            or expected_offset + len(chunk) > self.asset.size
        ):
            raise BlockedEvidence("cache_chunk_bounds")
        try:
            fd = self._open_partial()
            if os.fstat(fd).st_size != expected_offset:
                raise BlockedEvidence("cache_offset")
            self._verified = None
            os.lseek(fd, expected_offset, os.SEEK_SET)
            with memoryview(chunk) as view:
                written = 0
                while written < len(view):
                    count = os.write(fd, view[written:])
                    if count <= 0:
                        raise BlockedEvidence("cache_write_failed")
                    written += count
            os.fsync(fd)
        except BaseException:
            self.invalidate_partial(self.identity)
            raise BlockedEvidence("cache_write_failed") from None

    def inspect_partial(self, identity: Identity) -> tuple[int, str]:
        self._require(identity)
        try:
            fd = self._open_partial()
            before = _fingerprint(_private_file(fd))
            if before[2] != self.asset.size:
                raise BlockedEvidence("cache_length")
            os.lseek(fd, 0, os.SEEK_SET)
            digest = hashlib.sha256()
            remaining = self.asset.size
            while remaining:
                chunk = os.read(fd, min(remaining, 1024**2))
                if not chunk:
                    raise BlockedEvidence("cache_length")
                digest.update(chunk)
                remaining -= len(chunk)
            if os.read(fd, 1):
                raise BlockedEvidence("cache_length")
            after = _fingerprint(_private_file(fd))
            actual = digest.hexdigest()
            if before != after or actual != self.asset.sha256:
                raise BlockedEvidence("cache_integrity")
            self._verified = after
            return after[2], actual
        except BaseException:
            self.invalidate_partial(identity)
            raise BlockedEvidence("cache_integrity") from None

    def atomic_promote(self, identity: Identity) -> None:
        self._require(identity)
        renamed = False
        try:
            if self._verified is None or self._partial == -1:
                raise BlockedEvidence("cache_unverified")
            current = _fingerprint(_private_file(self._partial))
            named = os.stat(self._name("partial"), dir_fd=self._directory, follow_symlinks=False)
            if current != self._verified or _fingerprint(named) != current:
                raise BlockedEvidence("cache_changed_after_verification")
            try:
                os.stat(self._name("asset"), dir_fd=self._directory, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise BlockedEvidence("cache_final_exists")
            os.fsync(self._partial)
            os.replace(
                self._name("partial"),
                self._name("asset"),
                src_dir_fd=self._directory,
                dst_dir_fd=self._directory,
            )
            renamed = True
            final = os.stat(self._name("asset"), dir_fd=self._directory, follow_symlinks=False)
            _private_file(self._partial)
            # A second actor cannot consume this entry until this lock is released.
            # Detect name substitution before making the completed transaction visible.
            if (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns) != current[:4]:
                raise BlockedEvidence("cache_promotion_substituted")
            os.fsync(self._directory)
            self._promoted = True
            self._verified = None
            self._remove("checkpoint")
        except BaseException:
            if renamed:
                with suppress(BaseException):
                    self._remove("asset")
            with suppress(BaseException):
                self.invalidate_partial(identity)
            raise BlockedEvidence("cache_promotion_failed") from None

    def _remove(self, suffix: str) -> None:
        with suppress(FileNotFoundError):
            os.unlink(self._name(suffix), dir_fd=self._directory)

    def save_checkpoint(self, text: str) -> None:
        record = self._checkpoint(text)
        if record.received != self.offset():
            raise BlockedEvidence("checkpoint_offset")
        fd = -1
        try:
            self._remove("checkpoint-new")
            fd = os.open(
                self._name("checkpoint-new"),
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self._directory,
            )
            payload = record.model_dump_json().encode("ascii")
            if os.write(fd, payload) != len(payload):
                raise BlockedEvidence("checkpoint_write_failed")
            os.fsync(fd)
            os.replace(
                self._name("checkpoint-new"),
                self._name("checkpoint"),
                src_dir_fd=self._directory,
                dst_dir_fd=self._directory,
            )
            os.fsync(self._directory)
        except BaseException:
            for suffix in ("checkpoint-new", "checkpoint"):
                with suppress(BaseException):
                    self._remove(suffix)
            raise BlockedEvidence("checkpoint_write_failed") from None
        finally:
            if fd != -1:
                os.close(fd)

    def _checkpoint(self, text: str) -> TransferCheckpoint:
        self._require(self.identity)
        try:
            record = TransferCheckpoint.model_validate_json(text)
        except ValidationError:
            raise BlockedEvidence("checkpoint_invalid") from None
        if (
            record.preparation_sha256,
            record.repository_revision,
            record.asset_sha256,
        ) != self.identity:
            raise BlockedEvidence("checkpoint_identity")
        if record.source_mode != self.mode:
            raise BlockedEvidence("checkpoint_identity")
        return record

    def load_checkpoint(self) -> str:
        text = self.checkpoint_if_present()
        if text is None:
            raise BlockedEvidence("checkpoint_invalid")
        return text

    def checkpoint_if_present(self) -> str | None:
        """Only absence is optional; unsafe, stale or malformed metadata still fails."""
        self._require(self.identity)
        fd = -1
        try:
            try:
                fd = os.open(
                    self._name("checkpoint"),
                    os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                    dir_fd=self._directory,
                )
            except FileNotFoundError:
                return None
            if _private_file(fd).st_size > 4096:
                raise BlockedEvidence("checkpoint_size")
            text = os.read(fd, 4097).decode("ascii")
            record = self._checkpoint(text)
            if record.received != self.offset():
                raise BlockedEvidence("checkpoint_offset")
            return text
        except BaseException:
            raise BlockedEvidence("checkpoint_invalid") from None
        finally:
            if fd != -1:
                os.close(fd)

    def invalidate_partial(self, identity: Identity) -> None:
        self._require(identity)
        self._verified = None
        failed = False
        if self._partial != -1:
            fd, self._partial = self._partial, -1
            try:
                os.close(fd)
            except BaseException:
                failed = True
        for suffix in ("partial", "checkpoint", "checkpoint-new"):
            try:
                self._remove(suffix)
            except BaseException:
                failed = True
        if failed:
            raise BlockedEvidence("cache_invalidation_failed")

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if kind is not None and not self._promoted:
                self.invalidate_partial(self.identity)
        finally:
            self.close()

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        failure = False
        for fd in (self._partial, self._lock, self._directory):
            if fd != -1:
                try:
                    os.close(fd)
                except BaseException:
                    failure = True
        self._partial = self._lock = self._directory = -1
        if failure:
            raise BlockedEvidence("cache_close_failed")
