"""Exception hierarchy for dash_relay."""
from __future__ import annotations


class DashRelayError(Exception):
    """Base exception for dash_relay."""


class InstallError(DashRelayError):
    """Raised by ``relay.install()`` for lifecycle or registration violations.

    Triggers:
      * ``app.layout`` is None when ``install()`` is called.
      * ``install()`` is called twice on the same app.
      * Two registered handlers share a ``(bridge, action)`` key.
      * A handler declares pattern-matched ids in ``Output``/``State``.
    """


class InvalidEventError(DashRelayError):
    """Raised when an event payload is malformed."""


class UnsafeLayoutError(DashRelayError):
    """Raised by ``validate(strict=True)`` when issues are found."""
