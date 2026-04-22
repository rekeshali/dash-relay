"""The ``Action`` dependency primitive and the default bridge constant.

``Action`` slots into the same position Dash's ``Input`` would in a
callback's dependency list. It identifies a relay action name and the
bridge it travels on. If ``bridge=`` isn't given, the action uses
``DEFAULT_BRIDGE``.

Multiple ``Action(...)`` declarations in a single ``@relay.callback``
register the wrapped function as the handler for every listed
``(bridge, action)`` pair — alias semantics for the common
"close-or-dismiss" shape.
"""
from __future__ import annotations


DEFAULT_BRIDGE: str = "dash-relay-bridge"


class Action:
    """A relay action dependency.

    Args:
        name: The action name string. Required, non-empty.
        bridge: The bridge name to listen on. If ``None`` (the default),
            falls through to ``DEFAULT_BRIDGE`` at construction.

    The class normalizes ``bridge=None`` to ``DEFAULT_BRIDGE`` immediately,
    so ``Action("foo").bridge_id`` is always a concrete string. This keeps
    every (bridge, action) routing key well-defined at registration time.
    """

    __slots__ = ("name", "bridge_id")

    def __init__(self, name: str, *, bridge: str | None = None):
        if not isinstance(name, str):
            raise TypeError(
                f"Action(name): name must be a string (got {type(name).__name__})"
            )
        if not name.strip():
            raise ValueError("Action(name): name must be a non-empty string")
        if bridge is not None:
            if not isinstance(bridge, str):
                raise TypeError(
                    f"Action(bridge=): must be a string (got {type(bridge).__name__})"
                )
            if not bridge.strip():
                raise ValueError("Action(bridge=): must be a non-empty string when provided")
        self.name = name
        self.bridge_id = bridge if bridge is not None else DEFAULT_BRIDGE

    def __repr__(self) -> str:
        if self.bridge_id == DEFAULT_BRIDGE:
            return f"Action({self.name!r})"
        return f"Action({self.name!r}, bridge={self.bridge_id!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Action)
            and other.name == self.name
            and other.bridge_id == self.bridge_id
        )

    def __hash__(self) -> int:
        return hash(("Action", self.name, self.bridge_id))
