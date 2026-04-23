"""Tests for @relay.callback + Action + per-bridge dispatch."""
from __future__ import annotations

import pytest
from dash import Dash, Output, State, dcc, html, no_update

import dash_relay as relay
from dash_relay import Action, InstallError
from dash_relay.callback import _PENDING_CALLBACKS


@pytest.fixture(autouse=True)
def _isolate_pool():
    _PENDING_CALLBACKS.clear()
    yield
    _PENDING_CALLBACKS.clear()


def _app(*store_ids):
    app = Dash(__name__)
    app.layout = html.Div([dcc.Store(id=sid, data={}) for sid in store_ids])
    return app


# ---------------------------------------------------------------------------
# Action primitive
# ---------------------------------------------------------------------------


def test_action_default_bridge_resolves_to_default_constant():
    a = Action("close")
    assert a.bridge_id == relay.DEFAULT_BRIDGE


def test_action_explicit_bridge_kept_as_given():
    a = Action("close", bridge="cards")
    assert a.bridge_id == "cards"


def test_action_rejects_non_string_name():
    with pytest.raises(TypeError):
        Action(42)


def test_action_rejects_empty_name():
    with pytest.raises(ValueError):
        Action("")


def test_action_rejects_empty_bridge():
    with pytest.raises(ValueError):
        Action("close", bridge="")


def test_action_equality_includes_bridge():
    assert Action("a") == Action("a")
    assert Action("a", bridge="x") == Action("a", bridge="x")
    assert Action("a") != Action("a", bridge="x")


# ---------------------------------------------------------------------------
# Decorator parsing
# ---------------------------------------------------------------------------


def test_callback_requires_at_least_one_output():
    with pytest.raises(ValueError, match="at least one Output"):
        @relay.callback(Action("x"))
        def _(event): ...


def test_callback_requires_at_least_one_action():
    with pytest.raises(ValueError, match="at least one Action"):
        @relay.callback(Output("a", "data"))
        def _(): ...


def test_callback_rejects_unknown_dep_type():
    with pytest.raises(TypeError, match="unsupported dependency"):
        @relay.callback(Output("a", "data"), Action("x"), "bare-string")
        def _(event): ...


def test_callback_appends_to_pending_pool_with_source_location():
    @relay.callback(Output("a", "data"), Action("x"))
    def fn(event): return None

    assert len(_PENDING_CALLBACKS) == 1
    spec = _PENDING_CALLBACKS[0]
    assert spec.fn is fn
    assert spec.actions[0].name == "x"
    assert spec.source_file.endswith("test_callback.py")
    assert spec.source_line > 0


# ---------------------------------------------------------------------------
# install() drains pool / wires dispatchers
# ---------------------------------------------------------------------------


def test_install_drains_pending_pool():
    @relay.callback(Output("state", "data"), Action("bump"))
    def _(event): return None

    assert len(_PENDING_CALLBACKS) == 1
    app = _app("state")
    relay.install(app)
    assert len(_PENDING_CALLBACKS) == 0
    assert len(app._dash_relay_handlers) == 1


def test_install_handles_no_handlers():
    app = _app()
    relay.install(app)
    assert app._dash_relay_handlers == []


# ---------------------------------------------------------------------------
# Dispatcher routing
# ---------------------------------------------------------------------------


def _last_dispatcher(app, bridge_name=None):
    bridge_name = bridge_name or relay.DEFAULT_BRIDGE
    return app._dash_relay_bridge_plans[bridge_name].dispatch


def test_dispatcher_routes_event_to_matching_handler():
    @relay.callback(
        Output("state", "data"),
        Action("bump"),
        State("state", "data"),
    )
    def bump(event, current):
        return {"count": (current or {}).get("count", 0) + 1}

    app = _app("state")
    relay.install(app)
    dispatch = _last_dispatcher(app)

    result = dispatch({"action": "bump"}, {"count": 5})
    assert result == {"count": 6}


def test_dispatcher_unknown_action_returns_no_update():
    @relay.callback(Output("state", "data"), Action("known"))
    def _(event): return {"set": True}

    app = _app("state")
    relay.install(app)
    dispatch = _last_dispatcher(app)

    assert dispatch({"action": "missing"}) is no_update


def test_dispatcher_empty_event_returns_no_update():
    @relay.callback(Output("state", "data"), Action("known"))
    def _(event): return {"set": True}

    app = _app("state")
    relay.install(app)
    dispatch = _last_dispatcher(app)

    assert dispatch(None) is no_update
    assert dispatch({}) is no_update


def test_dispatcher_pads_no_update_for_outputs_other_handlers_touch():
    @relay.callback(Output("a", "data"), Action("touch-a"), State("a", "data"))
    def _(event, current): return {"a": True}

    @relay.callback(Output("b", "data"), Action("touch-b"), State("b", "data"))
    def _(event, current): return {"b": True}

    app = _app("a", "b")
    relay.install(app)
    dispatch = _last_dispatcher(app)

    # All handlers on default bridge → unioned dispatcher.
    result = dispatch({"action": "touch-a"}, {}, {})
    assert result == [{"a": True}, no_update]

    result = dispatch({"action": "touch-b"}, {}, {})
    assert result == [no_update, {"b": True}]


def test_dispatcher_passes_state_values_in_handler_declaration_order():
    @relay.callback(
        Output("write", "data"),
        Action("compute"),
        State("ctx2", "data"),
        State("ctx1", "data"),
    )
    def compute(event, ctx2, ctx1):
        return {"order": [ctx1, ctx2]}

    app = _app("write", "ctx1", "ctx2")
    relay.install(app)
    dispatch = _last_dispatcher(app)

    # Union state order is the order of first declaration. With one
    # handler, that's ctx2 then ctx1. Dispatcher signature: (event, ctx2, ctx1).
    result = dispatch({"action": "compute"}, "ctx2_value", "ctx1_value")
    assert result == {"order": ["ctx1_value", "ctx2_value"]}


def test_dispatcher_multi_output_tuple_return():
    @relay.callback(Output("a", "data"), Output("b", "data"), Action("set-both"))
    def _(event):
        return {"a_new": True}, {"b_new": True}

    app = _app("a", "b")
    relay.install(app)
    dispatch = _last_dispatcher(app)
    result = dispatch({"action": "set-both"})
    assert result == [{"a_new": True}, {"b_new": True}]


def test_dispatcher_multi_output_wrong_return_type_raises():
    @relay.callback(Output("a", "data"), Output("b", "data"), Action("oops"))
    def _(event):
        return {"a": 1}  # not a tuple

    app = _app("a", "b")
    relay.install(app)
    dispatch = _last_dispatcher(app)
    with pytest.raises(TypeError, match="must return a tuple"):
        dispatch({"action": "oops"})


def test_dispatcher_handler_no_update_skips_all_writes():
    @relay.callback(Output("a", "data"), Action("abort"), State("a", "data"))
    def _(event, current): return no_update

    app = _app("a")
    relay.install(app)
    dispatch = _last_dispatcher(app)
    assert dispatch({"action": "abort"}, {}) is no_update


# ---------------------------------------------------------------------------
# Multi-bridge: per-bridge dispatchers, isolated handler pools
# ---------------------------------------------------------------------------


def test_multi_bridge_each_bridge_gets_its_own_dispatcher_with_scoped_outputs():
    @relay.callback(
        Output("state-a", "data"),
        Action("bump", bridge="bridge-a"),
        State("state-a", "data"),
    )
    def bump_a(event, s): return {"count": (s or {}).get("count", 0) + 1}

    @relay.callback(
        Output("state-b", "data"),
        Action("bump", bridge="bridge-b"),
        State("state-b", "data"),
    )
    def bump_b(event, s): return {"count": (s or {}).get("count", 0) + 100}

    app = _app("state-a", "state-b")
    relay.install(app)

    # Two bridges → two dispatchers, each with its own scoped outputs.
    plan_a = app._dash_relay_bridge_plans["bridge-a"]
    plan_b = app._dash_relay_bridge_plans["bridge-b"]

    # Each plan has only ONE output (the one its handler writes).
    assert [o.component_id for o in plan_a.all_outputs] == ["state-a"]
    assert [o.component_id for o in plan_b.all_outputs] == ["state-b"]

    # Each dispatcher routes only its own action.
    assert plan_a.dispatch({"action": "bump"}, {"count": 0}) == {"count": 1}
    assert plan_b.dispatch({"action": "bump"}, {"count": 0}) == {"count": 100}


# ---------------------------------------------------------------------------
# Alias actions (B5)
# ---------------------------------------------------------------------------


def test_multiple_actions_in_one_callback_register_aliases():
    @relay.callback(
        Output("modal", "data"),
        Action("close", bridge="modal.signup"),
        Action("dismiss", bridge="modal.signup"),
        State("modal", "data"),
    )
    def close_or_dismiss(event, current):
        return {"is_open": False, "via": event["action"]}

    app = _app("modal")
    relay.install(app)

    plan = app._dash_relay_bridge_plans["modal.signup"]
    # Both action names route to the same handler in this bridge's lookup.
    assert plan.handlers_by_action["close"].fn is plan.handlers_by_action["dismiss"].fn

    result_a = plan.dispatch({"action": "close"}, {"is_open": True})
    result_b = plan.dispatch({"action": "dismiss"}, {"is_open": True})
    assert result_a == {"is_open": False, "via": "close"}
    assert result_b == {"is_open": False, "via": "dismiss"}


def test_aliases_do_not_collide_at_install():
    # Two Action(name=close) declarations in ONE callback are fine —
    # different names, both route here. (Spec B5 says alias.)
    @relay.callback(
        Output("a", "data"),
        Action("close", bridge="x"),
        Action("dismiss", bridge="x"),
    )
    def _(event): return None

    app = _app("a")
    relay.install(app)  # must not raise


# ---------------------------------------------------------------------------
# Collision detection (B4)
# ---------------------------------------------------------------------------


def test_two_handlers_same_bridge_action_raises_install_error():
    @relay.callback(Output("a", "data"), Action("close", bridge="x"))
    def _(event): return None

    @relay.callback(Output("a", "data"), Action("close", bridge="x"))
    def _(event): return None

    app = _app("a")
    with pytest.raises(InstallError, match="Duplicate handler"):
        relay.install(app)


def test_two_handlers_default_bridge_same_action_collide():
    @relay.callback(Output("a", "data"), Action("close"))
    def _(event): return None

    @relay.callback(Output("a", "data"), Action("close"))
    def _(event): return None

    app = _app("a")
    with pytest.raises(InstallError, match="Duplicate handler"):
        relay.install(app)


def test_same_action_name_different_bridges_no_collision():
    @relay.callback(Output("a", "data"), Action("close", bridge="bridge-a"))
    def _(event): return None

    @relay.callback(Output("b", "data"), Action("close", bridge="bridge-b"))
    def _(event): return None

    app = _app("a", "b")
    relay.install(app)  # must not raise


# ---------------------------------------------------------------------------
# B12: pattern-matched ids rejected
# ---------------------------------------------------------------------------


def test_pattern_matched_output_id_rejected_at_install():
    from dash import MATCH

    @relay.callback(
        Output({"type": "row", "id": MATCH}, "children"),
        Action("touch"),
    )
    def _(event): return None

    app = _app()
    with pytest.raises(InstallError, match="pattern-matched"):
        relay.install(app)


def test_pattern_matched_state_id_rejected_at_install():
    from dash import ALL

    @relay.callback(
        Output("a", "data"),
        Action("touch"),
        State({"type": "row", "id": ALL}, "value"),
    )
    def _(event, vals): return None

    app = _app("a")
    with pytest.raises(InstallError, match="pattern-matched"):
        relay.install(app)
