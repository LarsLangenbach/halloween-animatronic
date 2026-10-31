# Frank's statecharts: a node editor you can also vibe-code

Frank's face engine (`frank/engine/`, [docs/FACE_ENGINE.md](../../docs/FACE_ENGINE.md)) decides which conversation state his face is in: idle, greeting, listening, thinking, speaking, interrupted, and so on. In the engine that logic is Python code. Here the same logic is a chart file instead. Three things work on that file:

- **the node editor:** draw it, run it in a simulator, and change it by asking Claude in plain words;
- **Claude Code or a text editor:** a JSON file anyone (or any Claude) can read and edit;
- **the running engine:** it loads the chart and picks up a saved change within a second.

The first chart, [charts/frank.json](charts/frank.json), rebuilds the engine's own state logic as of 2026-10-30. A test runs both on the same scripted evening and checks that they give the same states, expressions and animator events.

## Files

| File | What it is |
|---|---|
| `chart.py` | The file format, the checker and the runtime (nested states, parallel regions, history, timers, guards). Standard library only. |
| `vocab.json` | What the face engine offers a chart: its events, the context it updates every tick, its actions and its profiles. The editor's dropdowns and Claude's instructions come from here. |
| `charts/*.json` | The charts. `frank.json` is Frank's. |
| `bridge.py` | `ChartedEngine`: the face engine with its states taken from a chart. A drop-in for `engine.Engine`. |
| `editor.py`, `editor.html` | The node editor, a local page on port 8830. |
| `api.py` | The editor's routes without a server: `api.handle(method, path, body, store)`. `editor.py` serves it over HTTP from the files in `charts/` (`FileStore`); the public site (`frank/online`) runs it in the browser on a `MemoryStore`, with `api.ONLINE = True` (vibe-coding off: it needs a key). |
| `vibe.py` | Sends a request and the chart to Claude, and brings back the changed chart. |
| `tests/` | `test_chart.py` (the runtime), `test_bridge.py` (chart against engine), `test_vibe.py` (vibe-coding with a stand-in for the API). |

## Running the editor

```
uv run --no-project --with anthropic python frank/statechart/editor.py
```

It opens http://localhost:8830. Vibe-coding needs the `anthropic` package (the `--with` above) and a key, `ANTHROPIC_API_KEY` in `frank/.env`, the same file the chat uses. Without them the rest of the editor works (`python frank/statechart/editor.py`). `--port` and `--model` change the defaults (port 8830, `claude-opus-5-5`). The editor only listens on this computer, and every change it makes needs a header that other websites can't send.

Ports in use: web.py 8800, the body twin 8810, the body socket 8811, the engine preview 8820, this editor 8830.

## Using it

- **Canvas.** Each box is a state. A box with states inside is a group, where one state is active at a time. A dashed box with ∥ holds parallel regions, which are all active at once. The colour shows the profile (what the face does). A black dot and arrow mark the state a group starts in.
- **Moving and connecting.**
  - Drag a box to move it, or drop it into another group to move it there.
  - Drag the small circle on a box's right edge onto another box to make a transition.
  - Double-click empty space or the inside of a group for a new state.
  - Scroll to zoom and drag the background to pan.
  - Delete removes the selection. Ctrl+Z / Ctrl+Y undo and redo; Ctrl+S saves.
- **Lines.** Solid lines are events. Dashed lines are timers (after N seconds). Dotted lines are conditions (when something becomes true). A small loop with a dot runs actions without changing state.
- **Inspect.** Edits the selected state or transition: its id, type and profile, actions on entry and exit, the trigger, guard, target and actions of each transition, and the order transitions are tried in. With nothing selected, it shows the chart's problems. Clicking a problem selects the state it's about.
- **Simulate.**
  - Runs the chart on a clock of its own, with the same Python runtime the engine uses.
  - You can tick the context (is he speaking, how many people are there), send events, step the clock or play it, and watch the active states light up green.
  - The log shows what fired and which actions would go to the engine.
- **Vibe.**
  - Say what you want ("after two minutes alone, let him get sleepy"). Claude sends back the whole chart, changed.
  - The canvas shows the change before you accept it: new states and transitions in green, changed ones in amber, with a list of what changed.
  - Accept applies it; Undo takes it back; nothing is saved until you press Save.
  - Questions ("explain this chart", "review it") get an answer in words.
  - If the chart Claude sends fails the checker, Claude gets the errors and one more go.
- **JSON.** Shows the chart without its layout, which you can edit by hand and apply.
- **Editing the file directly.** The page checks the open chart's file every 1.5 s. When it changes on disk (you asked Claude Code to edit it, or edited it yourself), the page reloads it, and Undo still takes you back. If you have unsaved changes too, it asks which version to keep. States added outside the editor get a place on the canvas automatically.

## Running Frank on a chart

`ChartedEngine` is `engine.Engine` with the state logic swapped out. Everything else is the engine's own: the synthesiser, the animator, the rig, the tag timing and the gaze.

```python
from statechart.bridge import ChartedEngine
engine = ChartedEngine(writer=mouth.Mouth("auto")).start()        # charts/frank.json
engine = ChartedEngine(chart="statechart/charts/mine.json").start()
```

On every 20 ms tick it:

1. updates the chart's context: `speaking`, `thinking`, `people`, `present`, `no_vision`;
2. runs the chart up to now;
3. carries out the chart's actions:
   - `tag`: an expression, on the engine's tag clock, honouring `delay`;
   - `nudge`: the mood;
   - `anim`: a one-shot blink, flinch, greet and so on;
   - `log`;
4. gives the animator the chart's profile.

The events the chat and the vision already send (`arrived`, `left`, `interrupted`, `hearing`, `visitor`, `frank_end`, ...) go into the chart. When the chart file is saved, the next tick loads it. A chart with errors is logged and the old one stays in charge, so a half-finished edit can't stop the face.

The chat (`chat.start_face()`) still starts the hand-written `Engine`. Switching it to `ChartedEngine` is a one-line change in `frank/chat.py`, which the face-engine session owns. It is not switched yet.

## The format, in short

The full specification is at the top of `chart.py`.

```json
{"format": "frank-statechart/1", "name": "frank", "host": "frank-engine",
 "root": {"id": "frank", "type": "parallel", "states": {
   "social": {"initial": "idle", "priority": 1, "states": {
     "idle":     {"profile": "idle", "transitions": [{"when": "people > 0", "target": "greeting"}]},
     "greeting": {"profile": "greeting",
                  "entry": [{"do": "anim", "event": "greet"}, {"do": "tag", "tag": "curious", "intensity": 0.6}],
                  "transitions": [{"after": 1.8, "target": "idle"}]}}}}},
 "layout": {"idle": {"x": 0, "y": 0, "w": 150, "h": 54}}}
```

**States.**
- Ids are unique across the whole chart.
- A state without `type` is a group if it has `states`, otherwise a plain state.
- `profile` is inherited from the nearest ancestor that has one. When parallel regions each give one, the higher `priority` wins.

**Transitions.** Each has exactly one trigger: `event`, `after` (seconds) or `when` (a condition). Each can also have a `guard`, a `target` (none means stay and only run the actions) and `actions`.

**How they run.**
- An event goes to the active state first, then to its ancestors, so a transition on a group covers all its states unless one handles the event itself.
- A transition to a state inside its source leaves only the source's child on the way.
- A transition to its own source leaves and re-enters it, which restarts its timers. Set `reenter` to change either default.
- Leaving one parallel region for another resets only those two regions.
- `when` transitions run until nothing more fires. A loop is stopped after 100 steps and reported.

**Expressions** are plain conditions over the context:
- `and`, `or`, `not`;
- comparisons and arithmetic;
- `in_state("id")`;
- `data["key"]` (the current event's data).

Nothing else is allowed, so a chart can't run code.

## Tests

```
.venv\Scripts\python.exe frank\statechart\tests\test_chart.py
.venv\Scripts\python.exe frank\statechart\tests\test_bridge.py
.venv\Scripts\python.exe frank\statechart\tests\test_vibe.py
```

None of them needs the head or a key. `test_bridge.py` imports the engine's orchestrator, so it also catches the engine and the chart drifting apart. On 2026-10-30 it caught the engine's new single-flinch rule for interruptions, now mirrored in `frank.json`.

## Not done yet

- **Knobs reach nothing.** A state's `knobs` merge by priority and show in the simulator, but the engine doesn't read any yet. They are the hook for blink rate, idle amount and so on, once the animator takes them.
- **No live Claude test.** Vibe-coding was tested against a stand-in for the API only. This Windows machine had no key, so a real request hasn't been made yet.
- **Not switched on.** The chat still runs the hand-written engine (see "Running Frank on a chart").
