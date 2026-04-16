# Pure Dash vs Liquid Dash

A side-by-side demo of the same toggleable, filterable, growable list,
implemented two ways in one Dash app. Each column has an in-page
console that logs every `_dash-update-component` fire attributed to its
side, so you can *see* the difference in callback activity.

```bash
python examples/pure_dash_pitfall/side_by_side.py
```

Both columns are functionally correct. Their consoles tell you why one
takes more code to keep correct than the other.

## What you're looking at

Both columns share the same UI: two starting items, an **Add item**
button, a **Toggle filter** button, and per-row toggle/delete buttons.
Both implementations work. The contrast is in the cost of correctness.

## The patterns at a glance

### Pure-Dash column

- One `Output("state", "data")` callback per action type. With four
  actions (filter, add, delete, toggle), that's four writers to the
  same store and a fifth callback for the renderer.
- The two per-row actions (delete, toggle) use pattern-matching
  Inputs (`Input({"type": "del", "index": ALL}, "n_clicks")`).
- `allow_duplicate=True` is required on three of the four writers so
  more than one callback can target the same `Output`.

### Liquid Dash column

- One client-side bridge (`dcc.Store`) receives every event.
- One server-side dispatch callback reads from the bridge and writes
  to the state store. That's it — two callbacks total, regardless of
  how many actions exist.
- Per-action handlers are registered against the dispatch callback
  via `@events.on("action")`.

## Where pure-Dash gets noisier

Watch the console while you click.

### Pattern-matching Inputs fire whenever the matched set changes

`Input({"type": "del", "index": ALL}, "n_clicks")` re-fires whenever
the *set of matching components* changes — adding an item, deleting
one, or filtering items in/out of the visible list all trigger it,
even when no delete button was actually clicked.

The fire returns `no_update` if the handler uses the canonical guard:

```python
if not ctx.triggered_id or ctx.triggered[0]["value"] is None:
    return no_update
```

Without that guard (or with the weaker `if not ctx.triggered_id`
alone), the body runs on phantom fires and silently mutates state.
Every pattern-matching ALL handler in your app needs to remember to
write the canonical guard.

The Liquid Dash column has one Input on the bridge store. The store
only updates when a real DOM event reaches it — adding, deleting, or
filtering rows triggers no extra dispatches.

### Round-trips per click scale with action types

Counted from the in-page consoles:

| | callbacks registered | round-trips per Add click |
|---|---|---|
| pure-Dash column | 5 (filter, add, delete, toggle, render) | 4 (add + render + 2 phantom round-trips that no_update) |
| Liquid Dash column | 2 (dispatch + render) | 2 (dispatch + render) |

The pure-Dash count grows with the number of action types and the
phantom round-trips grow with the number of pattern-matching
subscribers. Liquid Dash stays at 2 callbacks and 2 round-trips per
click no matter how many actions you add.

### Multiple writers + `allow_duplicate`

The pure-Dash column has four callbacks writing to `Output("state",
"data", allow_duplicate=True)`. Dash queues callbacks and dispatches
them serially within a request, so the everyday case is fine. The
risk is at scale: more writers + more pattern subscribers + faster
input cadence eventually hits coordination problems that production
apps solve with an idempotency layer or a single reducer.

The Liquid Dash column has one writer (`handler`'s dispatch callback)
against a single `Output`. There's nothing to coordinate.

## What Liquid Dash gives up to do this

Liquid Dash adds a client-side script (~120 lines) and one wrapper
`html.Div` per interactive element. Events flow through `dcc.Store`
which means they're not in the standard Dash callback graph — tools
that introspect the graph (e.g. the dev panel's callback view) won't
show per-action handlers, only the single dispatch callback.

If your app is a static layout with a fixed number of interactions,
plain Dash is simpler. Liquid Dash earns its keep when the layout is
dynamic and the number of action types is growing.
