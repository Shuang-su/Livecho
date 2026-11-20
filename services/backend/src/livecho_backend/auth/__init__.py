"""Issue #12 invite-only magic links and roles.

The default application keeps mail off and reads no process environment.
Production send, sealed secrets, and Postgres migrations are not wired here.
"""

from .app import create_auth_app
from .bootstrap import BootstrapError, bootstrap_first_admin

__all__ = [
    "BootstrapError",
    "bootstrap_first_admin",
    "create_auth_app",
]
