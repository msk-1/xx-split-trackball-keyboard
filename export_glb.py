#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# out/stl/asm/*.stl（アセンブリ座標）を 1 つの GLB にまとめる（web/index.html が読む）
# 形はここで作らない。寸法を変えるときは build.py を直して流し直す。
# 色・分解図のオフセット・単色の配色は preview.scad の表を読み、ノードの extras に入れる。
# -----------------------------------------------------------------------------
# 実行: python3 export_glb.py                                  # -> web/assembly-local.glb（手元用。git に入れない）
#       python3 export_glb.py --no-xiao -o web/assembly.glb    # -> 公開用（GitHub Pages に載る）
#   --no-xiao  XIAO のモデルを入れない（ref/xiao-nrf52840.step は再配布しないため、
#              公開する GLB・人に渡す GLB は必ずこれで作る）
#   --json     GLB を base64 で包んだ JSON も書く（.glb を配れない置き場所向け。index.html は
#              assembly.glb が無ければ assembly.json を読む）
# 依存: numpy だけ
# =============================================================================
import argparse
import json
import os
import re
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, "out", "stl", "asm")
SCAD = os.path.join(HERE, "preview.scad")


def read_scad_tables():
    src = open(SCAD, encoding="utf-8").read()
    parts_block = src.split("parts = [", 1)[1].split("];", 1)[0]
    mono_block = src.split("mono = [", 1)[1].split("];", 1)[0]
    right_block = src.split("right_only = [", 1)[1].split("];", 1)[0]
    parts = [(n, c, float(z)) for n, c, z in
             re.findall(r'\["([\w-]+)",\s*"(#[0-9A-Fa-f]{6})",\s*(-?[\d.]+)\]', parts_block)]
    mono = {n: {"black": b, "white": w, "darkgray": g} for n, b, w, g in
            re.findall(r'\["([\w-]+)",\s*"(#\w+)",\s*"(#\w+)",\s*"(#\w+)"\]', mono_block)}
    right_only = re.findall(r'"([\w-]+)"', right_block)
    return parts, mono, right_only


def read_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        v = re.findall(rb"vertex\s+(\S+)\s+(\S+)\s+(\S+)", data)
        tri = np.array(v, dtype=np.float64).reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", data[80:84])[0]
        rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                            count=n, offset=84)
        tri = rec["v"].astype(np.float64)
    flat = np.round(tri.reshape(-1, 3), 4)
    verts, inv = np.unique(flat, axis=0, return_inverse=True)
    idx = inv.reshape(-1, 3)
    idx = idx[(idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])]
    return verts.astype(np.float32), idx.astype(np.uint32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-xiao", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-o", "--out", default=os.path.join(HERE, "web", "assembly-local.glb"))
    args = ap.parse_args()

    parts, mono, right_only = read_scad_tables()
    buf = bytearray()
    views, accessors, meshes, nodes = [], [], [], []

    def add_view(b, target):
        while len(buf) % 4:
            buf.append(0)
        views.append({"buffer": 0, "byteOffset": len(buf), "byteLength": len(b), "target": target})
        buf.extend(b)
        return len(views) - 1

    for name, color, dz in parts:
        if args.no_xiao and name == "xiao":
            continue
        for side in ("left", "right"):
            if side == "left" and name in right_only:
                continue
            path = os.path.join(ASM, f"{name}-{side}.stl")
            if not os.path.exists(path):
                print("skip (missing):", path)
                continue
            v, idx = read_stl(path)
            if len(idx) == 0:
                continue
            small = len(v) < 65536
            ib = idx.astype(np.uint16 if small else np.uint32).tobytes()
            pv = add_view(v.tobytes(), 34962)
            accessors.append({"bufferView": pv, "componentType": 5126, "count": len(v), "type": "VEC3",
                              "min": v.min(0).tolist(), "max": v.max(0).tolist()})
            pa = len(accessors) - 1
            iv = add_view(ib, 34963)
            accessors.append({"bufferView": iv, "componentType": 5123 if small else 5125,
                              "count": idx.size, "type": "SCALAR"})
            ia = len(accessors) - 1
            meshes.append({"name": f"{name}-{side}", "primitives": [{"attributes": {"POSITION": pa}, "indices": ia}]})
            nodes.append({"name": f"{name}-{side}", "mesh": len(meshes) - 1,
                          "extras": {"part": name, "side": side, "color": color, "explode": dz,
                                     "mono": mono.get(name)}})
            print(f"{name}-{side}: {len(v)} verts, {len(idx)} tris")

    gltf = {
        "asset": {"version": "2.0", "generator": "export_glb.py"},
        "scene": 0,
        # build.py は z 上・mm。glTF は y 上・m なので、ルートで回して縮める
        "scenes": [{"nodes": [len(nodes)]}],
        "nodes": nodes + [{"name": "assembly", "children": list(range(len(nodes))),
                           "rotation": [-0.7071068, 0, 0, 0.7071068], "scale": [0.001] * 3}],
        "meshes": meshes, "accessors": accessors, "bufferViews": views,
        "buffers": [{"byteLength": len(buf)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    while len(buf) % 4:
        buf.append(0)
    total = 12 + 8 + len(js) + 8 + len(buf)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(buf), 0x004E4942) + bytes(buf))
    print(f"-> {args.out} ({total / 1e6:.1f} MB)")
    if args.json:
        import base64
        jp = os.path.splitext(args.out)[0] + ".json"
        with open(args.out, "rb") as f, open(jp, "w") as g:
            json.dump({"format": "glb-base64", "glb": base64.b64encode(f.read()).decode()}, g)
        print(f"-> {jp} ({os.path.getsize(jp) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
