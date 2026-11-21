"""Issue #13 worker invite registration, device identity, and statistics.

The application is unmounted by default. It keeps a process-local memory
adapter and does not enable production authentication.
"""

from .app import create_worker_identity_app

__all__ = ["create_worker_identity_app"]
