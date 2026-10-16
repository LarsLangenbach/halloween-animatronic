"""
M2 concept study: how should the brow carrier move under the skin?

The carrier holds the skin at two snap pads per brow (BROW_PADS_X, BROW_PAD
square), BROW_GAP behind the skin's inner surface, joined by a stiff bar that
sits deeper. It must move the pads BROW_RAISE up and BROW_LOWER down along the
skin at mid-brow, never push a pad more than BROW_PUSH_MAX toward the skin or
pull it more than BROW_PULL_MAX away, and move the inner pad BROW_INNER_BIAS
times as far as the outer one (D5).

Concepts (PLAN M2, decision D3):
  A          one rigid plate across the whole brow, on one pivot axis parallel
             to x behind mid-brow (the first idea; kept as the reference)
  P  (pads)  the two-pad carrier on one pivot axis, with the pivot position
             (distance behind the brow, height) and the axis skew in plan
             searched for the best fit
  B / C      a four-bar or a curved track are only worth their extra parts if
             P cannot meet the limits

The left brow (+x) is computed; the right one is its mirror image. All
geometry comes from geom.front_y, the same surface the proxy head is built from.

Run:  python cad/studies/brow_concepts.py
  -> <out>/studies/brow_concepts.md and brow_concepts.png
"""
import itertools
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cadkit as K  # noqa: E402
import geom as G  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
P = K.params()
S = P.HEAD_SCALE
EZ = G.eye_z(S)
ZB = EZ + P.BROW_LINE_Z                   # brow line height
INSET = P.SKIN_T + P.BROW_GAP             # carrier face below the outer skin
XM = (P.BROW_INNER_X + P.BROW_OUTER_X) / 2
TRAVEL = np.linspace(-P.BROW_LOWER, P.BROW_RAISE, 16)
PIVOT_MIN_DEPTH = 8.0                     # mm: the pivot sits at least this far behind the carrier face


def carrier_y(x, z):
    return G.front_y(x, z, S, INSET)


def normals(x, z, h=0.5):
    """Outward unit normals of the carrier surface at points (x, z)."""
    dydx = (carrier_y(x + h, z) - carrier_y(x - h, z)) / (2 * h)
    dydz = (carrier_y(x, z + h) - carrier_y(x, z - h)) / (2 * h)
    n = np.column_stack([-dydx, np.ones_like(dydx), -dydz])
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def grid(xs, zs):
    X, Z = np.meshgrid(xs, zs)
    x, z = X.ravel(), Z.ravel()
    return np.column_stack([x, carrier_y(x, z), z])


def plate_points():
    return grid(np.linspace(P.BROW_INNER_X, P.BROW_OUTER_X, 13), ZB + np.linspace(-8, 8, 5))


def pad_points():
    h = P.BROW_PAD / 2
    return np.vstack([grid(np.linspace(px - h, px + h, 5), ZB + np.linspace(-h, h, 5)) for px in P.BROW_PADS_X])


def rotate(pts, origin, axis, angle):
    axis = axis / np.linalg.norm(axis)
    p = pts - origin
    c, s = math.cos(angle), math.sin(angle)
    return origin + p * c + np.cross(axis, p) * s + np.outer(p @ axis, axis) * (1 - c)


def gap_change(pts):
    """+ = toward the skin (push), - = away (pull), along the local normal."""
    return (pts[:, 1] - carrier_y(pts[:, 0], pts[:, 2])) * normals(pts[:, 0], pts[:, 2])[:, 1]


def sweep(pts, pivot, axis, ref):
    """Rigid rotation about (pivot, axis); the angle per pose moves `ref` (the
    mid-brow point) by the travel along its arc. Returns (push, pull, poses)."""
    d = ref - pivot
    rm = np.linalg.norm(d - (d @ axis) * axis)
    push, pull, poses = 0.0, 0.0, {}
    for t in TRAVEL:
        moved = rotate(pts, pivot, axis, t / rm)
        g = gap_change(moved)
        push, pull = max(push, float(np.nanmax(g))), max(pull, float(-np.nanmin(g)))
        poses[round(float(t), 1)] = moved
    return push, pull, poses, rm


def evaluate(pts, r, offset, beta_deg):
    """Pivot r behind mid-brow along the normal, moved `offset` along the
    surface's upward tangent; axis skewed beta in plan."""
    ref = np.array([XM, float(carrier_y(XM, ZB)), ZB])
    n = normals(np.array([XM]), np.array([ZB]))[0]
    up = np.cross(np.array([1.0, 0.0, 0.0]), n)        # tangent pointing up the face
    up /= np.linalg.norm(up)
    pivot = ref - r * n + offset * up
    b = math.radians(beta_deg)
    axis = np.array([math.cos(b), math.sin(b), 0.0])
    push, pull, poses, rm = sweep(pts, pivot, axis, ref)
    ends = np.array([[px, float(carrier_y(px, ZB)), ZB] for px in P.BROW_PADS_X])
    rise = rotate(ends, pivot, axis, P.BROW_RAISE / rm)[:, 2] - ends[:, 2]
    depth = float(carrier_y(pivot[0], pivot[2]) - pivot[1])
    return dict(r=r, offset=offset, beta=beta_deg, push=push, pull=pull, inner=float(rise[0]),
                outer=float(rise[1]), bias=float(rise[0] / rise[1]), pivot=pivot, poses=poses,
                depth=depth, axis=axis)


def feasible(e):
    in_bay = (P.BROW_BAY_Y[0] + 15 <= e["pivot"][1] and EZ + P.BROW_BAND_Z[0] <= e["pivot"][2] <= EZ + P.BROW_BAY_Z[1]
              and e["depth"] >= PIVOT_MIN_DEPTH)
    return (in_bay and e["push"] <= P.BROW_PUSH_MAX and e["pull"] <= P.BROW_PULL_MAX
            and abs(e["bias"] - P.BROW_INNER_BIAS) <= 0.1)


def main():
    out_dir = os.path.join(K.check_out(), "studies")
    os.makedirs(out_dir, exist_ok=True)
    plate, pads = plate_points(), pad_points()
    # A: the first idea, a whole-brow plate on an axis along x, for reference
    ref_rows = []
    for r in (20.0, 30.0, 40.0, 50.0, 70.0):
        a = evaluate(plate, r, 0.0, 0.0)
        ref_rows.append(f"| {r:.0f} | {a['push']:.1f} | {a['pull']:.1f} | {a['inner']:.1f} / {a['outer']:.1f} |")
    # P: two pads, search pivot distance, offset along the face and skew
    results = []
    for r, off, beta in itertools.product(np.arange(15.0, 75.1, 5.0), np.arange(-20.0, 20.1, 4.0),
                                          np.arange(-24.0, 24.1, 3.0)):
        results.append(evaluate(pads, r, off, beta))
    ok = [e for e in results if feasible(e)]
    score = lambda e: max(e["push"] / P.BROW_PUSH_MAX, e["pull"] / P.BROW_PULL_MAX)  # noqa: E731
    best = min(ok, key=score) if ok else min(results, key=lambda e: score(e) + abs(e["bias"] - P.BROW_INNER_BIAS))
    top = sorted(ok, key=score)[:8]

    md = ["# M2 brow concept study", "",
          f"Left brow, head scale {S}. Brow line z {ZB:.1f} ({P.BROW_LINE_Z} above the eye line). Carrier face "
          f"{P.BROW_GAP} behind the skin's inner surface. Travel at mid-brow (x {XM:.0f}): +{P.BROW_RAISE} / "
          f"-{P.BROW_LOWER} along the skin. Limits: push <= {P.BROW_PUSH_MAX}, pull <= {P.BROW_PULL_MAX}, "
          f"inner/outer rise {P.BROW_INNER_BIAS} +- 0.1 (D5).", "",
          "## A: one plate across the whole brow, axis along x (reference)", "",
          "| r behind the brow | worst push | worst pull | inner / outer rise |", "|---|---|---|---|"] + ref_rows + [
          "", "A rigid plate 46 mm wide can't follow the face as it curves back toward the temple: it either digs "
              "into the skin or lifts off by several mm. Hence the two-pad carrier.", "",
          f"## P: two snap pads (|x| {P.BROW_PADS_X[0]:.0f} and {P.BROW_PADS_X[1]:.0f}, {P.BROW_PAD:.0f} mm square) on one axis",
          "", f"Searched {len(results)} pivots (r 15..75, offset along the face -20..20, skew -24..24 deg); "
              f"{len(ok)} meet every limit with the pivot inside the brow bay. Best ones:", "",
          "| r | offset | skew deg | pivot (y, z above eyes) | push | pull | inner / outer rise |",
          "|---|---|---|---|---|---|---|"]
    md += [f"| {e['r']:.0f} | {e['offset']:+.0f} | {e['beta']:+.0f} | ({e['pivot'][1]:.1f}, {e['pivot'][2] - EZ:.1f}) | "
           f"{e['push']:.2f} | {e['pull']:.2f} | {e['inner']:.1f} / {e['outer']:.1f} |" for e in top] or ["| none |"]
    b = best
    md += ["", (f"**Pick: r {b['r']:.0f}, offset {b['offset']:+.0f}, skew {b['beta']:+.0f} deg.** "
                if ok else "**No pivot meets every limit; closest:** ")
           + f"Pivot at x {b['pivot'][0]:.1f}, y {b['pivot'][1]:.1f}, z {b['pivot'][2]:.1f} "
             f"(eye line + {b['pivot'][2] - EZ:.1f}), {b['depth']:.1f} behind the carrier face; axis "
             f"({b['axis'][0]:.3f}, {b['axis'][1]:.3f}, 0). Pads move {b['push']:.2f} toward / {b['pull']:.2f} away "
             f"from the skin; inner pad rises {b['inner']:.1f}, outer {b['outer']:.1f} at full raise. "
             f"Servo rotation for full travel: +{math.degrees(P.BROW_RAISE / np.linalg.norm(b['poses'][0.0][0] - b['pivot'])):.0f} "
             f"/ -{math.degrees(P.BROW_LOWER / np.linalg.norm(b['poses'][0.0][0] - b['pivot'])):.0f} deg (approx.)."]
    with open(os.path.join(out_dir, "brow_concepts.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md[5:]))
    plot(best, evaluate(plate, 40.0, 0.0, 0.0), out_dir)
    print("\nBROW STUDY OK" if ok else "\nBROW STUDY: no pivot meets the limits")
    return 0


def plot(best, plate_ref, out_dir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.4))
    cols = {-P.BROW_LOWER: "tab:blue", 0.0: "tab:green", P.BROW_RAISE: "tab:red"}
    # 1: side section through the inner pad
    for ax, px, title in ((axs[0], P.BROW_PADS_X[0], "inner pad"), (axs[1], P.BROW_PADS_X[1], "outer pad")):
        z = np.linspace(EZ, EZ + 70, 200)
        ax.plot(G.front_y(px, z, S, 0.0), z - EZ, "k-", label="outer skin")
        ax.plot(G.front_y(px, z, S, P.SKIN_T), z - EZ, "-", color="grey", label="skin inner surface")
        ax.plot(G.front_y(px, z, S, INSET), z - EZ, "--", color="grey", label="pad face at rest")
        for t, c in cols.items():
            pts = best["poses"][round(float(t), 1)]
            sel = np.abs(pts[:, 0] - px) < 0.01 + P.BROW_PAD / 2
            ax.plot(pts[sel, 1], pts[sel, 2] - EZ, ".", color=c, ms=4, label=f"pad at {t:+.0f}")
        pv = best["pivot"]
        ax.plot(pv[1], pv[2] - EZ, "k^", ms=9, label="pivot")
        ax.set_title(f"side section x = {px:.0f} ({title})")
        ax.set_xlabel("y (mm, + = out of the face)")
        ax.set_ylabel("height above the eye line (mm)")
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, loc="lower left")
    # 3: front view: pads at the three poses, and the reference plate's centre line
    ax = axs[2]
    for t, c in cols.items():
        pts = best["poses"][round(float(t), 1)]
        for px in P.BROW_PADS_X:
            sel = np.abs(pts[:, 0] - px) < 0.01 + P.BROW_PAD / 2
            ax.plot(pts[sel, 0], pts[sel, 2] - EZ, "s", color=c, ms=3)
        cen = [pts[np.abs(pts[:, 0] - px) < 0.01 + P.BROW_PAD / 2].mean(axis=0) for px in P.BROW_PADS_X]
        ax.plot([c_[0] for c_ in cen], [c_[2] - EZ for c_ in cen], "-", color=c, label=f"pads at {t:+.0f}")
    ax.axhline(0, color="k", lw=0.8)
    ax.text(P.EYE_SPACING / 2, -3, "eye centre", ha="center", fontsize=8)
    ax.plot([P.EYE_SPACING / 2], [0], "ko")
    ax.set_title("front view (character's left brow): neutral, raised, lowered")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("height above the eye line (mm)")
    ax.set_xlim(0, 70)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.suptitle(f"M2 brow concept: two snap pads on one pivot (r {best['r']:.0f}, skew {best['beta']:+.0f} deg); "
                 f"push {best['push']:.2f} / pull {best['pull']:.2f} mm; inner/outer rise "
                 f"{best['inner']:.1f}/{best['outer']:.1f} mm", fontsize=12)
    fig.tight_layout()
    path = os.path.join(out_dir, "brow_concepts.png")
    fig.savefig(path, dpi=110)
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())
