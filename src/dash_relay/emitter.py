"""The ``Emitter`` template class.

An ``Emitter`` is a reusable template of relay-event metadata. The same
template can be materialized two ways:

  * ``.attrs(...)`` — returns a dict of ``data-relay-*`` HTML attributes
    suitable for splatting onto an existing component (no wrapper Div,
    so CSS ``>`` child selectors and direct-child flex/grid still work).
  * ``.wrap(component, ...)`` — wraps the given component in a transparent
    ``display: contents`` div carrying the attributes; convenient when
    you don't want to (or can't) splat onto the target.

Both methods accept overrides via keyword arguments. **Override
semantics are replace, not merge.** To merge a payload, do it
explicitly: ``payload={**e.payload, "scope": new_scope}``.
"""
from __future__ import annotations

import json
from typing import Any

from dash import html

from .action import DEFAULT_BRIDGE


_TEMPLATE_KEYS = (
    "action",
    "bridge",
    "target",
    "payload",
    "source",
    "on",
    "prevent_default",
)


class Emitter:
    """Reusable template for relay-event emission.

    All constructor fields are optional; overrides at ``.wrap()`` /
    ``.attrs()`` time replace the corresponding template field.

    The ``action`` field is required by the time you call ``.wrap()`` or
    ``.attrs()``. If neither the template nor the overrides set it,
    materialization raises ``ValueError``. ``bridge`` defaults to
    ``DEFAULT_BRIDGE`` if unset on both sides.
    """

    def __init__(
        self,
        action: str | None = None,
        bridge: str | None = None,
        target: Any = None,
        payload: dict | None = None,
        source: str | None = None,
        on: str = "click",
        prevent_default: bool = False,
    ):
        self.action = action
        self.bridge = bridge
        self.target = target
        self.payload = payload
        self.source = source
        self.on = on
        self.prevent_default = prevent_default

    # -- materialization -----------------------------------------------------

    def attrs(self, **overrides) -> dict:
        """Return a dict of ``data-relay-*`` attributes.

        Splat onto an existing Dash component:

            html.Button("Pin", **emitter.attrs(action="pin", target=row_id))

        Useful when you can't accept a wrapper Div (CSS direct-child
        selectors, flex/grid child positioning, etc.).
        """
        merged = self._merge(overrides)
        return _build_attrs(merged)

    def wrap(self, component, **overrides):
        """Return ``component`` wrapped in a transparent div carrying the attrs.

        Equivalent to ``html.Div([component], style={'display': 'contents'},
        **self.attrs(**overrides))``. Use this when splatting onto the
        component isn't possible (e.g. third-party components that
        don't forward arbitrary HTML attributes).

        If ``source`` isn't set on either the template or the overrides,
        and the wrapped component has an ``id=``, ``source`` is auto-filled
        with that id.
        """
        merged = self._merge(overrides)
        # B9: auto-fill source from component id if neither side specified one.
        if merged.get("source") is None:
            cid = _component_id(component)
            if isinstance(cid, str):
                merged["source"] = cid
        attrs = _build_attrs(merged)
        return html.Div([component], style={"display": "contents"}, **attrs)

    # -- internals -----------------------------------------------------------

    def _merge(self, overrides: dict) -> dict:
        unknown = set(overrides) - set(_TEMPLATE_KEYS)
        if unknown:
            raise TypeError(
                f"Emitter override got unexpected keyword(s): {sorted(unknown)}. "
                f"Allowed: {list(_TEMPLATE_KEYS)}."
            )
        merged = {k: getattr(self, k) for k in _TEMPLATE_KEYS}
        # Replace, not merge — overrides are absolute.
        merged.update(overrides)
        return merged


# ---------------------------------------------------------------------------
# Attribute building
# ---------------------------------------------------------------------------


def _component_id(component) -> Any:
    if hasattr(component, "to_plotly_json"):
        return component.to_plotly_json().get("props", {}).get("id")
    if hasattr(component, "id"):
        return getattr(component, "id", None)
    return None


def _encode_target(target: Any) -> str:
    """Encode a target value for the DOM ``data-relay-target`` attribute (B10).

    Plain string for ``str`` and ``int``; compact JSON for ``dict``. The
    encoding is selectable by CSS attribute selectors without escape
    gymnastics. Tradeoff: a ``str`` value that happens to look like a
    digit string round-trips as ``int`` because the wire encoding is
    lossy on that distinction. If you need a digit-string preserved,
    wrap it in a dict (e.g. ``target={"id": "42"}``).
    """
    if target is None:
        return ""
    if isinstance(target, bool):
        # bool is a subclass of int — handle explicitly so True doesn't
        # encode as "1" silently.
        raise TypeError(
            "Emitter target must be str, int, or dict — got bool. "
            "Wrap in a dict if you need to carry a boolean."
        )
    if isinstance(target, (str, int)):
        return str(target)
    if isinstance(target, dict):
        try:
            return json.dumps(target, separators=(",", ":"))
        except TypeError as exc:
            raise ValueError(
                "Emitter target dict must be JSON-serializable"
            ) from exc
    raise TypeError(
        f"Emitter target must be str, int, or dict (got {type(target).__name__})"
    )


def _encode_payload(payload: Any) -> str:
    """Payload is always JSON-encoded — it's a dict by contract."""
    if payload is None:
        return ""
    if not isinstance(payload, dict):
        raise TypeError(
            f"Emitter payload must be a dict (got {type(payload).__name__})"
        )
    try:
        return json.dumps(payload, separators=(",", ":"))
    except TypeError as exc:
        raise ValueError("Emitter payload must be JSON-serializable") from exc


def _build_attrs(merged: dict) -> dict:
    action = merged.get("action")
    if action is None or not str(action).strip():
        raise ValueError(
            "Emitter requires an action; set on constructor or at "
            "wrap()/attrs() time."
        )
    bridge = merged.get("bridge") or DEFAULT_BRIDGE
    on = merged.get("on") or "click"
    if not isinstance(on, str) or not on.strip():
        raise ValueError("Emitter 'on' must be a non-empty string")

    attrs = {
        "data-relay-action": str(action),
        "data-relay-bridge": bridge,
        "data-relay-on": on,
        "data-relay-target": _encode_target(merged.get("target")),
        "data-relay-payload": _encode_payload(merged.get("payload")),
        "data-relay-source": str(merged.get("source")) if merged.get("source") is not None else "",
        "data-relay-prevent-default": "true" if merged.get("prevent_default") else "false",
    }
    return attrs
