from dash import Dash, html

import dash_relay as relay


def test_install_registers_js_route_and_injects_script_tag() -> None:
    app = Dash(__name__)
    app.layout = html.Div()
    relay.install(app)

    assert '<script src="/_dash_relay/dash_relay.js"></script>' in app.index_string

    client = app.server.test_client()
    response = client.get("/_dash_relay/dash_relay.js")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/javascript")
    assert "__dashRelayInstalled" in response.get_data(as_text=True)


def test_install_is_idempotent() -> None:
    app = Dash(__name__)
    relay.install(app)
    relay.install(app)

    assert app.index_string.count('src="/_dash_relay/dash_relay.js"') == 1
