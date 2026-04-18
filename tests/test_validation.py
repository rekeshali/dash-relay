from dash import dcc, html

import dash_relay as relay


def test_validate_flags_missing_bridge() -> None:
    # Action targets a bridge id that doesn't exist as a dcc.Store in the layout.
    layout = html.Div(
        [
            dcc.Store(id="bridge"),  # default bridge, but action points elsewhere
            relay.emitter(html.Button("Delete"), "card.delete", to="ghost-bus"),
        ]
    )
    report = relay.validate(layout)
    codes = {issue.code for issue in report.issues}
    assert "missing-bridge" in codes


def test_validate_flags_duplicate_ids() -> None:
    layout = html.Div(
        [
            dcc.Store(id="dup"),
            html.Div(id="dup"),
        ]
    )
    report = relay.validate(layout)
    codes = {issue.code for issue in report.issues}
    assert "duplicate-id" in codes


def test_validate_passes_on_clean_layout() -> None:
    layout = html.Div(
        [
            relay.bridge(),
            relay.emitter(html.Button("Add"), "add"),
            relay.emitter(html.Button("Delete"), "delete", target="row-1"),
        ]
    )
    report = relay.validate(layout)
    assert report.ok, f"unexpected issues: {report.issues}"
