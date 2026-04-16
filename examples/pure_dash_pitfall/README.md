# Pure Dash vs Liquid Dash

Nested workspace surface — Folders → Tabs → Panels with 9 action types
across 3 entity levels — implemented two ways in one Dash app. Each
column calls the same state-mutation helpers. Only the wiring between
the UI and those helpers differs.

```bash
python examples/pure_dash_pitfall/nested_side_by_side.py
```

Each column has a **▶ Run test** button that plays the same 9-click
sequence against its side. Below each timeline, a running summary
tracks cumulative activity:

```
Tests run: N    Round-trips: N    Total: N KB    Total time: N s
```

## Measured contrast (one test run = 9 clicks)

| | callback graph | round-trips | bytes | wall time |
|---|---|---|---|---|
| Pure Dash column | 10 callbacks | ~88 | ~108 KB | ~5.9 s |
| Liquid Dash column | 2 callbacks + 9 reducers | ~18 | ~18 KB | ~5.6 s |

Both columns take about the same wall-clock time (debounce-dominated),
but Pure Dash sends ~6× the round-trips and ~6× the bytes. The gap
widens per extra test run because payloads carry bigger state.

### What "2 callbacks + 9 reducers" means

Both sides have the same number of *actions* (9). The difference is
whether those actions are first-class Dash callbacks.

- **Pure Dash:** one Dash callback per action type (9) + renderer (1) =
  **10 in the callback graph**. Every entry is a pattern-matching
  subscriber. Adding a new action adds a new pattern callback.
- **Liquid Dash:** one Dash callback for dispatch (1) + renderer (1) =
  **2 in the callback graph**. Per-action logic lives as 9 reducers
  registered on the dispatch callback's action registry
  (`@events.on("action")`). Adding a new action is a new reducer — not
  a new Dash callback, not a new pattern-matching subscriber, no new
  phantom-fire surface.

The callback *graph* is what carries cost. Reducers are Python dict
lookups at dispatch time — they don't phantom-fire, don't subscribe
to layout, don't compete for `allow_duplicate` writes.

## Why the gap exists

### 1. Pattern-matching Inputs subscribe to layout

`Input({"type": "del", "index": ALL}, "n_clicks")` re-fires whenever
the set of matching components changes. In a nested dynamic surface,
every `folder.add`, `tab.add`, `panel.delete`, etc. reshapes several
pattern sets at once. Even with the canonical guard
(`if not ctx.triggered_id or ctx.triggered[0]["value"] is None: return
no_update`), the server still does the round-trip to return
`no_update` — and ships the full State store with it.

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

## What Liquid Dash trades away

Liquid Dash adds a client-side script (~120 lines) and one wrapper
`html.Div` per interactive element. Events flow through `dcc.Store`
rather than the standard Dash callback graph, so tools that introspect
that graph (e.g. the dev panel's callback view) show only the single
dispatch callback, not per-action handlers.

If your app is a static layout with a fixed number of interactions,
plain Dash is simpler. Liquid Dash earns its keep when the layout is
dynamic, entities nest, and the number of action types is growing.
