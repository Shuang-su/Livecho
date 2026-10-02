"""Local eager-load boundary only; it cannot establish a fresh process or Cold row.

No backend is installed. A later trusted process runner must establish no prior model
or warmup and hardware/privacy prerequisites before using these local load boundaries.
"""

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal, Protocol

from .cache_reader import FinalModelCache, VerifiedModelReader
from .contracts import NS, InferenceManifest
from .instrumentation import ExecutionGuard
from .runtime import BlockedEvidence


class EagerModelBackend(Protocol):
    provider_revision: str
    dependency_lock_sha256: str

    @property
    def unloaded(self) -> bool: ...

    def initialize(
        self,
        manifest: InferenceManifest,
        assets: Mapping[str, VerifiedModelReader],
        *,
        local_files_only: Literal[True],
        trust_remote_code: Literal[False],
    ) -> None:
        """Consume borrowed handles eagerly; no path/network access or individual close.

        Equal-content labels share a reader lifetime. The load owner closes readers.
        """
        ...

    def synchronize(self) -> None: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class LocalLoadBoundaries:
    load_start_ns: int
    ready_ns: int


@contextmanager
def local_model_load(
    cache: FinalModelCache,
    backend: EagerModelBackend,
    *,
    clock: Callable[[], int],
    guard: ExecutionGuard,
    cancelled: Callable[[], bool],
) -> Iterator[LocalLoadBoundaries]:
    """Own cache/backend through exit; release every reader before yielding readiness.

    The injected backend's unloaded flag, revision properties and local-only parameters
    are an interface contract, not proof about its code or the host. This does not add
    registration, model execution or process-freshness evidence. The guard must terminate
    an in-flight operation before returning/raising; a real guard is still absent.
    """
    failure: BaseException | None = None
    try:
        if (
            backend.unloaded is not True
            or backend.provider_revision != cache.manifest.provider_revision
            or backend.dependency_lock_sha256 != cache.manifest.dependency_lock_sha256
        ):
            raise BlockedEvidence("load_backend_mismatch")
        start = clock()
        if type(start) is not int or start < 0:
            raise BlockedEvidence("invalid_timing")
        ready = start
        completed = False

        def load() -> None:
            nonlocal ready, completed
            if cancelled():
                raise BlockedEvidence("cancelled")
            assets = cache.open_assets(cancelled)
            backend.initialize(
                cache.manifest, assets, local_files_only=True, trust_remote_code=False
            )
            if cancelled():
                raise BlockedEvidence("cancelled")
            backend.synchronize()
            for reader in assets.values():
                reader.validate()
            if backend.unloaded is not False or cancelled():
                raise BlockedEvidence("load_not_ready")
            # Include reader cleanup in the guarded transaction and ready boundary.
            cache.close()
            ready = clock()
            if type(ready) is not int or not start <= ready <= start + 30 * NS:
                raise BlockedEvidence("load_timing")
            completed = True

        guard.execute(load, start + 30 * NS)
        if not completed:
            raise BlockedEvidence("load_not_ready")
        # A backend retaining handles cannot read them after the load transaction.
        if cancelled():
            raise BlockedEvidence("cancelled")
        yield LocalLoadBoundaries(start, ready)
    except BaseException as error:
        failure = error
    finally:
        cleanup_failed = False
        for cleanup in (cache.close, backend.close):
            try:
                cleanup()
            except BaseException:
                cleanup_failed = True
        if cleanup_failed:
            raise BlockedEvidence("load_cleanup_failed") from None
    if failure is not None:
        if isinstance(failure, BlockedEvidence):
            raise failure
        raise BlockedEvidence("local_load_failed") from None
