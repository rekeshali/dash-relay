# Pure Dash vs Liquid Dash

Two side-by-side demos. Each has a pure-Dash column and a Liquid Dash
column running the same UI against the same state-mutation helpers.
Each column has an in-page console that logs every
`_dash-update-component` fire attributed to its side.

```bash
# Simple flat surface: toggleable/filterable/growable list, 4 actions
python examples/pure_dash_pitfall/side_by_side.py

# Nested surface: Folders -> Tabs -> Panels, 9 actions across 3 levels
python examples/pure_dash_pitfall/nested_side_by_side.py
```

At the small scale of `side_by_side.py`, pure Dash is fine with the
canonical guards. Where the choice starts to matter is
`nested_side_by_side.py`, where 9 action types across unbounded nested
entities make the pure-Dash callback graph and per-click round-trip
count grow in ways Liquid Dash doesn't.

## Measured contrast in `nested_side_by_side.py`

Both columns implement the same folder → tab → panel surface. They call
the same mutation helpers. The difference is the wiring between the UI
and those helpers.

| | callbacks registered | round-trips per click (typical) |
|---|---|---|
| Pure Dash column | 10 (one per action type + renderer) | 8–10 (1 real + render + 6–8 phantom no_update round-trips) |
| Liquid Dash column | 2 (dispatch + renderer) | 2 |

The pure-Dash number grows as you add action types. Every
pattern-matching ALL callback fires on every layout change whose
matched set changes, even when the user's click was for an unrelated
action. Canonical guards keep them correct (they return `no_update`),
but the round-trips happen and scale with the number of pattern
callbacks.

Liquid Dash stays at 2 callbacks regardless of action types or entity
counts, and per-click round-trips stay at 2.

## The three patterns that create the gap

### 1. Pattern-matching Inputs subscribe to layout

`Input({"type": "del", "index": ALL}, "n_clicks")` re-fires whenever
the set of matching components changes. In a nested dynamic surface,
every `folder.add`, `tab.add`, `panel.delete`, etc. reshapes several
pattern sets at once. Even with the canonical guard
(`if not ctx.triggered_id or ctx.triggered[0]["value"] is None: return
no_update`), the server still does the round-trip to return
`no_update`.

### 2. Payload threads awkwardly through pattern IDs

`panel.add` wants a `kind`. In pure Dash, the idiomatic fix is to put
the kind in the pattern ID: `{"type": "panel-add", "kind": ALL}`. That
works, but multi-parameter actions (e.g. `panel.badge.cycle` needing
panel_id + badge_index) leak more data into the ID dict. With Liquid
Dash, the JSON `payload` field carries whatever shape you want.

### 3. Multiple writers to one store

Every pure-Dash action callback writes to `canvas.data` with
`allow_duplicate=True`. Ten writers against one store work, but any
invariant you want to maintain (e.g. undo, optimistic updates) has to
account for all ten writers. Liquid Dash has one writer — the
dispatch callback — so invariants live in one place.

## Why the small demo (`side_by_side.py`) doesn't show this

At 4 actions on a flat list, pure Dash with canonical guards is fine.
Both columns fire 2–4 round-trips per click, both stay consistent, and
the 3-callback overhead isn't visible. The contrast only opens up when
action types multiply and entities nest — hence the second demo.

## What Liquid Dash trades away

Liquid Dash adds a client-side script (~120 lines) and one wrapper
`html.Div` per interactive element. Events flow through `dcc.Store`
rather than the standard Dash callback graph, so tools that introspect
that graph (e.g. the dev panel's callback view) show only the single
dispatch callback, not per-action handlers.

If your app is a static layout with a fixed number of interactions,
plain Dash is simpler. Liquid Dash earns its keep when the layout is
dynamic, entities nest, and the number of action types is growing.
