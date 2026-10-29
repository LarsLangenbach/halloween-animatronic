"""
Bake-off: the same test conversations (scenarios.py) through each candidate brain, timed,
with a blind rating page for the creators.

    uv run --no-project --with anthropic --with openai python frank/bakeoff.py
    uv run ... frank/bakeoff.py --models haiku-5.5,gpt-5.4-mini --only child,inject
    uv run ... frank/bakeoff.py --dry-run     (no API calls: checks the plumbing and the page)
    uv run ... frank/bakeoff.py --score output/frank/bakeoff/<run>  [ratings files...]

A run writes output/frank/bakeoff/<date_time>/:
    results.json  every reply, its timing and checks, with model names
    key.json      which letter is which model in each scenario (don't open it before rating)
    rate.html     the blind rating page: open it in a browser, rate, press "Save ratings"
Put each rater's saved ratings_*.json in the run folder (or name them after the folder),
then --score prints the unblinded table and writes summary.md.

Timing: "first sentence" is from sending the request to the first whole sentence the voice
could start on, which is what a visitor waits for (plus speech-to-text and the voice's
own start-up). Models that aren't set up in frank/.env are skipped.
"""

import argparse
import json
import random
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import brain  # noqa: E402
import speech  # noqa: E402
from scenarios import SCENARIOS  # noqa: E402

OUT = HERE.parent / "output" / "frank" / "bakeoff"
TOOL_RESULTS = {"remember_person": "Remembered.", "forget_person": "Forgotten: face and memories deleted."}
LEADING_TAG = re.compile(r"\s*\[(%s)\]" % "|".join(
    speech.FACES + tuple(a for a, f in speech.ALIASES.items() if f in speech.FACES)), re.I)
MARKDOWN = re.compile(r"[*#`]|^\s*[-•]\s", re.M)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")


# --- running -----------------------------------------------------------------

def run_turn(convo, t):
    results = {cid: TOOL_RESULTS.get(name, "done") for cid, name, _ in convo.pending}
    convo.add_turn(t["say"], t["notes"], results)
    tags = speech.TagStream()
    rec = dict(text="", events=[], tools=[], first_token=None, first_face=None, first_say=None)
    t0 = time.perf_counter()
    try:
        for ev in convo.stream():
            now = round(time.perf_counter() - t0, 3)
            out = []
            if ev[0] == "text":
                rec["first_token"] = rec["first_token"] or now
                rec["text"] += ev[1]
                out = tags.feed(ev[1])
            elif ev[0] == "tool":
                rec["tools"].append(dict(name=ev[1], input=ev[2], valid=brain.valid_input(ev[1], ev[2])))
            else:
                rec["info"] = ev[1]
                out = tags.flush()
            for kind, value in out:
                rec["events"].append([round(now, 3), kind, value])
                if kind == "face" and rec["first_face"] is None:
                    rec["first_face"] = now
                if kind == "say" and rec["first_say"] is None:
                    rec["first_say"] = now
    except Exception as e:  # recorded, and the scenario stops for this model
        rec["error"] = f"{type(e).__name__}: {e}"
    rec["total"] = round(time.perf_counter() - t0, 3)
    rec["unknown_tags"] = tags.unknown
    rec["flags"] = flags(rec, convo)
    return rec


def flags(rec, convo):
    f = []
    text, info = rec["text"], rec.get("info", {})
    if "error" in rec:
        f.append("error")
    if text.strip() and not LEADING_TAG.match(text):
        f.append("no leading tag")
    if rec["unknown_tags"]:
        f.append("unknown tags: " + ", ".join(rec["unknown_tags"]))
    if MARKDOWN.search(text):
        f.append("markdown")
    if EMOJI.search(text):
        f.append("emoji")
    if sum(1 for e in rec["events"] if e[1] == "say") > 3:
        f.append("long (4+ sentences)")
    if info.get("stop_reason") == "refusal":
        f.append("refusal")
    if info.get("served_by") and not str(info["served_by"]).startswith(convo.cfg["model"]):
        f.append(f"served by {info['served_by']}")
    if any(not t["valid"] for t in rec["tools"]):
        f.append("invalid tool input")
    return f


def run_model(name, scenarios, dry):
    out = {}
    for sc in scenarios:
        convo = FakeConversation(name) if dry else brain.Conversation(name)
        out[sc["id"]] = []
        for t in sc["turns"]:
            rec = run_turn(convo, t)
            out[sc["id"]].append(rec)
            print(f"  {name:13} {sc['id']:13} {secs(rec['first_say']):>6}  "
                  f"{(rec.get('error') or rec['text'])[:70]!r}", flush=True)
            if "error" in rec:
                break
    return out


class FakeConversation:
    """Stands in for brain.Conversation in --dry-run."""
    REPLIES = ["[curious] Oh, hello. I don't think we've met. [amused] Have you come far?",
               "[concentrating] Hmm. [skeptical] I suppose that's one way of looking at it.",
               "[surprised] Oh! [chuckle] Well, that was unexpected."]

    def __init__(self, name):
        self.cfg = {"model": name}
        self.pending, self.n, self.said = [], 0, ""

    def add_turn(self, said, notes=(), tool_results=None):
        self.pending, self.said = [], said

    def stream(self):
        reply = self.REPLIES[self.n % len(self.REPLIES)]
        self.n += 1
        time.sleep(0.2)
        for i in range(0, len(reply), 6):
            time.sleep(0.01)
            yield ("text", reply[i:i + 6])
        if "remember" in self.said.lower() or "yes please" in self.said.lower():
            self.pending.append(("call_1", "remember_person", {"first_name": "Priya", "notes": "a nurse"}))
            yield ("tool", "remember_person", {"first_name": "Priya", "notes": "a nurse"})
        yield ("done", dict(stop_reason="end_turn", served_by=self.cfg["model"]))


# --- reporting ---------------------------------------------------------------

def secs(x):
    return "-" if x is None else f"{x:.2f}s"


def timing(results, name):
    firsts = [r["first_say"] for turns in results[name].values() for r in turns
              if r["first_say"] is not None and "error" not in r]
    if not firsts:
        return dict(n=0, median=None, p90=None, worst=None)
    firsts.sort()
    return dict(n=len(firsts), median=statistics.median(firsts),
                p90=firsts[min(len(firsts) - 1, int(0.9 * len(firsts)))], worst=firsts[-1])


def tool_check(results, name, scenarios):
    """Scenarios where the model called exactly the expected tools."""
    right = []
    for sc in scenarios:
        turns = results[name].get(sc["id"], [])
        called = sorted(t["name"] for r in turns for t in r["tools"])
        right.append(called == sorted(sc.get("expect_tools", [])))
    return sum(right), len(right)


def print_timings(results, scenarios):
    print(f"\n{'model':14} {'replies':>7} {'1st sentence: median':>21} {'p90':>6} {'worst':>6}"
          f" {'flagged':>8} {'tools right':>12}")
    for name in results:
        t = timing(results, name)
        flagged = sum(1 for turns in results[name].values() for r in turns if r["flags"])
        ok, total = tool_check(results, name, scenarios)
        print(f"{name:14} {t['n']:7} {secs(t['median']):>21} {secs(t['p90']):>6} {secs(t['worst']):>6}"
              f" {flagged:8} {f'{ok}/{total}':>12}")


def write_rating_page(run_dir, scenarios, results, key):
    data = {"run": run_dir.name, "scenarios": []}
    for sc in scenarios:
        letters = key[sc["id"]]
        data["scenarios"].append(dict(
            id=sc["id"], title=sc["title"], turns=sc["turns"],
            replies={letter: [dict(text=r["text"], tools=r["tools"], error=r.get("error"))
                              for r in results[name].get(sc["id"], [])]
                     for letter, name in sorted(letters.items())}))
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (run_dir / "rate.html").write_text(RATE_HTML.replace("__DATA__", blob), encoding="utf-8")


def score(paths):
    run_dir = Path(paths[0])
    run = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    key = json.loads((run_dir / "key.json").read_text(encoding="utf-8"))
    files = [Path(p) for p in paths[1:]] or sorted(run_dir.glob("ratings*.json"))
    if not files:
        sys.exit(f"No ratings files given or found in {run_dir}")
    scores = {name: [] for name in run["results"]}
    notes = []
    for f in files:
        r = json.loads(f.read_text(encoding="utf-8"))
        for sc_id, by_letter in r["ratings"].items():
            for letter, v in by_letter.items():
                name = key[sc_id][letter]
                if v.get("score"):
                    scores[name].append(v["score"])
                if v.get("note"):
                    notes.append(f"- {r.get('rater') or f.stem} on {sc_id}, {name}: {v['note']}")

    scenarios = run["scenarios"]
    lines = [f"# Bake-off {run_dir.name}", "",
             f"Raters: {', '.join(f.name for f in files)}", "",
             "| model | mean rating | ratings | 1st sentence median | p90 | flagged replies | tools right |",
             "|---|---|---|---|---|---|---|"]
    order = sorted(scores, key=lambda n: -(statistics.mean(scores[n]) if scores[n] else 0))
    for name in order:
        t = timing(run["results"], name)
        flagged = sum(1 for turns in run["results"][name].values() for r in turns if r["flags"])
        ok, total = tool_check(run["results"], name, scenarios)
        mean = f"{statistics.mean(scores[name]):.2f}" if scores[name] else "-"
        lines.append(f"| {name} | {mean} | {len(scores[name])} | {secs(t['median'])} | "
                     f"{secs(t['p90'])} | {flagged} | {ok}/{total} |")
    lines += ["", "## Flagged replies", ""]
    for name in run["results"]:
        for sc_id, turns in run["results"][name].items():
            for i, r in enumerate(turns, 1):
                if r["flags"]:
                    lines.append(f"- {name}, {sc_id} turn {i}: {'; '.join(r['flags'])}: "
                                 f"{(r.get('error') or r['text'])[:100]!r}")
    lines += ["", "## Raters' notes", ""] + (notes or ["(none)"])
    text = "\n".join(lines) + "\n"
    (run_dir / "summary.md").write_text(text, encoding="utf-8")
    print(text)


# --- main --------------------------------------------------------------------

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Frank's brain bake-off")
    ap.add_argument("--models", default=",".join(brain.MODELS), help="comma-separated, from brain.MODELS")
    ap.add_argument("--only", help="comma-separated scenario ids")
    ap.add_argument("--dry-run", action="store_true", help="no API calls")
    ap.add_argument("--score", nargs="+", metavar="PATH", help="run folder, then optional ratings files")
    args = ap.parse_args()
    if args.score:
        return score(args.score)

    brain.load_env()
    names = [n for n in args.models.split(",") if n]
    bad = [n for n in names if n not in brain.MODELS]
    if bad:
        sys.exit(f"Unknown model(s) {bad}; choose from {list(brain.MODELS)}")
    if not args.dry_run:
        skipped = [n for n in names if not brain.available(n)]
        for n in skipped:
            print(f"skipping {n}: set {brain.KEY_ENV[brain.MODELS[n]['provider']]} in frank/.env")
        names = [n for n in names if n not in skipped]
        if not names:
            sys.exit("No model has credentials. Copy frank/.env.example to frank/.env and add keys.")
    scenarios = SCENARIOS
    if args.only:
        wanted = args.only.split(",")
        scenarios = [s for s in SCENARIOS if s["id"] in wanted]

    run_dir = OUT / (datetime.now().strftime("%Y-%m-%d_%H%M") + ("_dry" if args.dry_run else ""))
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(names)} model(s) x {len(scenarios)} scenarios -> {run_dir}")
    with ThreadPoolExecutor(len(names)) as ex:  # one thread per model; its scenarios run in order
        results = dict(zip(names, ex.map(lambda n: run_model(n, scenarios, args.dry_run), names)))

    letters = "ABCDEFGHIJ"
    key = {}
    for sc in scenarios:
        shuffled = random.sample(names, len(names))
        key[sc["id"]] = {letters[i]: n for i, n in enumerate(shuffled)}
    created = datetime.now().isoformat(timespec="seconds")
    (run_dir / "results.json").write_text(json.dumps(dict(
        created=created, dry_run=args.dry_run, models={n: brain.MODELS[n] for n in names},
        scenarios=scenarios, results=results), indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (run_dir / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    write_rating_page(run_dir, scenarios, results, key)
    print_timings(results, scenarios)
    print(f"\nRate the replies blind: {run_dir / 'rate.html'}")


RATE_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frank bake-off</title>
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#1d1d1b;--mute:#6b6a65;--line:#dedbd2;--accent:#3d6b4f;--tag:#e7efe9;--warn:#a2462e}
@media (prefers-color-scheme:dark){:root{--bg:#161715;--card:#202220;--ink:#ecebe6;--mute:#a09e97;--line:#383a36;--accent:#8fc4a1;--tag:#2b3a30;--warn:#e08a70}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}h1{font-size:22px;margin:0 0 4px}
.lede{color:var(--mute);margin:0 0 20px}.bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:2;border-bottom:1px solid var(--line)}
input,textarea,button{font:inherit;color:inherit}input[type=text]{padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card)}
button{padding:6px 14px;border:1px solid var(--accent);background:var(--accent);color:var(--bg);border-radius:6px;cursor:pointer}
.count{color:var(--mute);font-size:13px}section{margin-top:28px}h2{font-size:17px;margin:0 0 6px}
.visitor{color:var(--mute);font-size:14px;margin:0 0 10px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.letter{font-weight:700;color:var(--accent);margin-bottom:6px}.say{margin:2px 0 2px}.who{color:var(--mute);font-size:13px}
.note{color:var(--mute);font-size:12px;font-style:italic}.tag{display:inline-block;background:var(--tag);border-radius:4px;padding:0 5px;font-size:12px;margin:0 2px}
.tool{display:inline-block;border:1px dashed var(--accent);border-radius:4px;padding:0 6px;font-size:12px}.err{color:var(--warn);font-size:13px}
.rate{display:flex;gap:6px;align-items:center;margin-top:10px;flex-wrap:wrap}.rate label{border:1px solid var(--line);border-radius:6px;padding:2px 10px;cursor:pointer}
.rate input{display:none}.rate input:checked+span{font-weight:700;color:var(--accent)}textarea{width:100%;margin-top:8px;border:1px solid var(--line);border-radius:6px;background:var(--card);padding:6px 8px;min-height:34px}
</style></head><body><main>
<h1>Frank bake-off: rate blind</h1>
<p class="lede">Each card is one model's side of the same conversation, in a shuffled order. Rate how much each sounds like Frank: 1 = wrong, 3 = fine, 5 = exactly him. Tags show where his face changes; dashed boxes are tool calls.</p>
<div class="bar"><input type="text" id="rater" placeholder="Your name"><button id="save">Save ratings</button><span class="count" id="count"></span></div>
<div id="list"></div></main>
<script type="application/json" id="data">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const KEY='frank-bakeoff-'+D.run;let R={};try{R=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const keep=()=>{try{localStorage.setItem(KEY,JSON.stringify(R))}catch(e){};count()};
const el=(t,c,txt)=>{const e=document.createElement(t);if(c)e.className=c;if(txt!=null)e.textContent=txt;return e};
function frank(text){const p=el('div','say');p.append(el('span','who','Frank: '));
  for(const part of text.split(/(\\[[^\\]]{0,40}\\])/)){if(!part)continue;
    if(/^\\[.*\\]$/.test(part))p.append(el('span','tag',part.slice(1,-1)));else p.append(document.createTextNode(part))}
  return p}
function count(){let n=0,t=0;for(const s of D.scenarios)for(const l in s.replies){t++;if(R[s.id]?.[l]?.score)n++}
  document.getElementById('count').textContent=n+' of '+t+' rated'}
const list=document.getElementById('list');
D.scenarios.forEach((s,i)=>{const sec=el('section');sec.append(el('h2',null,(i+1)+'. '+s.title));
  const v=el('div','visitor');s.turns.forEach((t,k)=>{v.append(el('div',null,'Visitor '+(k+1)+': '+t.say));
    t.notes.forEach(n=>v.append(el('div','note',n)))});sec.append(v);
  for(const [letter,turns] of Object.entries(s.replies)){const c=el('div','card');c.append(el('div','letter',letter));
    turns.forEach((r,k)=>{c.append(el('div','who','after visitor '+(k+1)));if(r.text)c.append(frank(r.text));
      r.tools.forEach(t=>c.append(el('span','tool','calls '+t.name+' '+JSON.stringify(t.input))));
      if(r.error)c.append(el('div','err',r.error))});
    const rate=el('div','rate');rate.append(el('span','who','Rating:'));
    for(let n=1;n<=5;n++){const lab=el('label');const inp=el('input');inp.type='radio';inp.name=s.id+letter;inp.value=n;
      if(R[s.id]?.[letter]?.score===n)inp.checked=true;
      inp.onchange=()=>{(R[s.id]??={})[letter]??={};R[s.id][letter].score=n;keep()};lab.append(inp,el('span',null,n));rate.append(lab)}
    const note=el('textarea');note.placeholder='Note (optional)';note.value=R[s.id]?.[letter]?.note||'';
    note.oninput=()=>{(R[s.id]??={})[letter]??={};R[s.id][letter].note=note.value;keep()};
    c.append(rate,note);sec.append(c)}
  list.append(sec)});
count();
document.getElementById('save').onclick=()=>{const who=document.getElementById('rater').value.trim()||'rater';
  const blob=new Blob([JSON.stringify({run:D.run,rater:who,ratings:R},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='ratings_'+who.replace(/\\W+/g,'_')+'.json';a.click()};
</script></body></html>
"""

if __name__ == "__main__":
    main()
