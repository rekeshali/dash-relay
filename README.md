# liquid-dash

A small library for building **more dynamic Dash interfaces** without turning your app into a maze of fragile callback wiring.

![liquid-dash demo](examples/workspace_demo/liquid-dash-demo.gif)

## Why this exists

Dash works really well when your layout is mostly known ahead of time.

It starts to get awkward when your interface becomes more dynamic and composable:

* parts of the layout are created and removed at runtime
* interactive regions are rebuilt often
* the same interaction pattern appears in many places
* controls inside rebuilt regions still need to behave reliably
* application state needs to stay coherent as the structure changes

At that point, callback wiring often becomes more complicated than the interaction itself.
Logic gets repeated. Plumbing starts to spread through the app. Simple actions stop feeling simple.

`liquid-dash` is a small layer for that specific situation.

## The pattern

The idea is simple:

* dynamic interface elements emit small action messages
* one stable event bridge receives those actions
* your app updates state from the action
* the interface rerenders from state

So instead of treating every interactive element as its own special callback surface, you can treat it more like:

> “an interaction happened, here is where to route it, now update state”

That keeps dynamic behavior easier to follow and easier to reuse.

This is not a replacement for Dash, and it is not a full framework.
It is just a focused utility layer for dynamic, state-driven interfaces.

## Where it helps

This may be useful if your Dash app has things like:

* interfaces that are assembled, modified, and rebuilt at runtime
* nested interactive structure
* reusable editing surfaces
* state-driven composition

If your app is mostly static, you probably do not need this.

## Core pieces

* `EventBridge` — a stable place for UI actions to land
* `StableRegion` — marks a part of the layout that should stay stable
* `DynamicRegion` — marks a part of the layout that may be rebuilt often
* `action_button`, `action_div`, `action_item` — helpers for elements that emit actions
* `validate_layout` — basic checks for common mistakes

## Installation

```bash
pip install liquid-dash
```

## Examples

### Simple live test

A small example that shows the core interaction pattern.

```bash
python examples/live_test/app.py
```

### Workspace demo

A larger example that applies the same pattern to a more complex nested interface with:

* multiple structural levels
* repeated structural changes
* shared editing surfaces
* state-driven rerendering
* lots of dynamic actions without a huge amount of repeated callback plumbing

```bash
python examples/workspace_demo/app.py
```

The GIF at the top of this README comes from this demo.

## Development

```bash
pip install -e .
pytest
```

## License

MIT
