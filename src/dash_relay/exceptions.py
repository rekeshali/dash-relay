class DashRelayError(Exception):
    """Base exception for dash_relay."""


class InvalidEventError(DashRelayError):
    """Raised when an event payload is malformed."""


class UnsafeLayoutError(DashRelayError):
    """Raised when the validator finds an unsafe layout."""
