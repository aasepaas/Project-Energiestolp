"""
Sync the level 3 container views (3.1 - 3.7) with the overview '3 - Components'.

Every component inside a container gets exactly the same position, size and
internal edges as in the '3 - Components' view. External elements (other
containers and actors) are placed around the container on the side where they
sit in the overview.

The result is written as LikeC4 manual layouts to .likec4/<viewId>.likec4.snap.

Usage (from the repository root or from this folder):
    python architecture/sync_component_layouts.py

Run it again whenever the model or the '3 - Components' layout changes.
"""

import json
import math
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OVERVIEW_VIEW = "components"
SNAP_DIR = os.path.join(HERE, ".likec4")
GAP = 140  # distance between the container and external elements


def export_views():
    """Export the computed and layouted views with the LikeC4 CLI."""
    out = os.path.join(tempfile.mkdtemp(), "model.json")
    cmd = f'npx likec4 export json -o "{out}"'
    subprocess.run(cmd, cwd=HERE, shell=True, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    return data[0] if isinstance(data, list) else data


def read_snapshot(view_id):
    """Return a saved manual layout, or None. Snapshots are JSON5; LikeC4 writes them without comments."""
    path = os.path.join(SNAP_DIR, f"{view_id}.likec4.snap")
    if not os.path.exists(path):
        return None
    try:
        import json5  # optional dependency
        with open(path, encoding="utf-8") as f:
            return json5.load(f)
    except ImportError:
        print(f"  note: install 'json5' to use the manual layout of '{view_id}'; using auto layout")
        return None


def rect(n):
    return n["x"], n["y"], n["width"], n["height"]


def center(n):
    x, y, w, h = rect(n)
    return x + w / 2, y + h / 2


def border_point(n, towards):
    """Point on the border of node n in the direction of point 'towards'."""
    cx, cy = center(n)
    dx, dy = towards[0] - cx, towards[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    hw, hh = n["width"] / 2, n["height"] / 2
    scale = min(hw / abs(dx) if dx else math.inf, hh / abs(dy) if dy else math.inf)
    return cx + dx * scale, cy + dy * scale


def straight_edge(src, tgt, label):
    p0 = border_point(src, center(tgt))
    p3 = border_point(tgt, center(src))
    pts = [[p0[0] + (p3[0] - p0[0]) * t, p0[1] + (p3[1] - p0[1]) * t] for t in (0, 1 / 3, 2 / 3, 1)]
    pts = [[round(x), round(y)] for x, y in pts]
    mx, my = (p0[0] + p3[0]) / 2, (p0[1] + p3[1]) / 2
    width = max(40, int(len(label or "") * 7))
    bbox = {"x": round(mx + 6), "y": round(my - 9), "width": width, "height": 18}
    return pts, bbox


def shift_points(points, dx, dy):
    return [[p[0] + dx, p[1] + dy] for p in points]


def shift_bbox(b, dx, dy):
    return None if b is None else {**b, "x": b["x"] + dx, "y": b["y"] + dy}


def place_externals(root, externals, overview_nodes, ox, oy):
    """Place external nodes on the side of the container where they sit in the overview."""
    rx, ry, rw, rh = rect(root)
    rcx, rcy = rx + rw / 2, ry + rh / 2
    sides = {"left": [], "right": [], "top": [], "bottom": []}
    for n in externals:
        ref = overview_nodes.get(n["id"])
        if ref is None:
            ex, ey = rcx, ry - 1
        else:
            ex, ey = center(ref)
            ex, ey = ex - ox, ey - oy
        dx, dy = ex - rcx, ey - rcy
        if abs(dx) / max(rw, 1) > abs(dy) / max(rh, 1):
            side = "right" if dx > 0 else "left"
        else:
            side = "bottom" if dy > 0 else "top"
        sides[side].append((n, ex, ey))

    for side, items in sides.items():
        horizontal = side in ("top", "bottom")
        items.sort(key=lambda t: t[1] if horizontal else t[2])
        cursor = -math.inf
        for n, ex, ey in items:
            w, h = n["width"], n["height"]
            if horizontal:
                x = min(max(ex - w / 2, rx - w / 2), rx + rw - w / 2)
                x = max(x, cursor)
                cursor = x + w + 40
                y = ry - GAP - h if side == "top" else ry + rh + GAP
            else:
                y = min(max(ey - h / 2, ry - h / 2), ry + rh - h / 2)
                y = max(y, cursor)
                cursor = y + h + 40
                x = rx - GAP - w if side == "left" else rx + rw + GAP
            n["x"], n["y"] = round(x), round(y)
            lb = n.get("labelBBox")
            # labelBBox of a leaf node is relative to the node, so it stays as is
            n["labelBBox"] = lb


def normalise(view):
    xs, ys = [], []
    for n in view["nodes"]:
        x, y, w, h = rect(n)
        xs += [x, x + w]
        ys += [y, y + h]
    for e in view["edges"]:
        for p in e.get("points", []):
            xs.append(p[0])
            ys.append(p[1])
        b = e.get("labelBBox")
        if b:
            xs += [b["x"], b["x"] + b["width"]]
            ys += [b["y"], b["y"] + b["height"]]
    minx, miny = min(xs), min(ys)
    dx, dy = -minx, -miny
    for n in view["nodes"]:
        n["x"] += dx
        n["y"] += dy
    for e in view["edges"]:
        e["points"] = shift_points(e["points"], dx, dy)
        if "controlPoints" in e and e["controlPoints"]:
            e["controlPoints"] = [{**c, "x": c["x"] + dx, "y": c["y"] + dy} for c in e["controlPoints"]]
        e["labelBBox"] = shift_bbox(e.get("labelBBox"), dx, dy)
    view["bounds"] = {"x": 0, "y": 0, "width": round(max(xs) - minx), "height": round(max(ys) - miny)}


def sync_view(view, overview):
    root_id = view["viewOf"]
    ov_nodes = {n["id"]: n for n in overview["nodes"]}
    ov_edges = {(e["source"], e["target"]): e for e in overview["edges"]}
    if root_id not in ov_nodes:
        print(f"  skip {view['id']}: {root_id} is not in the overview")
        return None

    ox, oy = ov_nodes[root_id]["x"], ov_nodes[root_id]["y"]

    def internal(node_id):
        return node_id == root_id or node_id.startswith(root_id + ".")

    externals = []
    for n in view["nodes"]:
        if internal(n["id"]):
            ref = ov_nodes.get(n["id"])
            if ref is None:
                continue
            n["x"], n["y"] = ref["x"] - ox, ref["y"] - oy
            n["width"], n["height"] = ref["width"], ref["height"]
            n["labelBBox"] = ref.get("labelBBox", n.get("labelBBox"))
        else:
            externals.append(n)

    root = next(n for n in view["nodes"] if n["id"] == root_id)
    place_externals(root, externals, ov_nodes, ox, oy)

    nodes = {n["id"]: n for n in view["nodes"]}
    for e in view["edges"]:
        ref = ov_edges.get((e["source"], e["target"]))
        if internal(e["source"]) and internal(e["target"]) and ref is not None:
            e["points"] = shift_points(ref["points"], -ox, -oy)
            if ref.get("controlPoints"):
                e["controlPoints"] = [{**c, "x": c["x"] - ox, "y": c["y"] - oy} for c in ref["controlPoints"]]
            else:
                e.pop("controlPoints", None)
            e["labelBBox"] = shift_bbox(ref.get("labelBBox"), -ox, -oy)
        else:
            e["points"], e["labelBBox"] = straight_edge(nodes[e["source"]], nodes[e["target"]], e.get("label"))
            e.pop("controlPoints", None)

    normalise(view)
    view.pop("_layout", None)
    view.pop("manualLayout", None)
    return view


def main():
    print("Exporting views with LikeC4 ...")
    data = export_views()
    views = data["views"]
    if OVERVIEW_VIEW not in views:
        sys.exit(f"View '{OVERVIEW_VIEW}' not found")

    overview = read_snapshot(OVERVIEW_VIEW) or views[OVERVIEW_VIEW]
    os.makedirs(SNAP_DIR, exist_ok=True)

    for view_id, view in views.items():
        of = view.get("viewOf") or ""
        # level 3 views: scoped to a container directly inside the system
        if of.count(".") != 1 or view_id == OVERVIEW_VIEW:
            continue
        synced = sync_view(json.loads(json.dumps(view)), overview)
        if synced is None:
            continue
        path = os.path.join(SNAP_DIR, f"{view_id}.likec4.snap")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(synced, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  synced {view_id:<20} -> .likec4/{view_id}.likec4.snap")
    print("Done. Restart 'npx likec4 start' if it is running.")


if __name__ == "__main__":
    main()
