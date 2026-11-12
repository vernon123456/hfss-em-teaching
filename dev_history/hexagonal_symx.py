# -*- coding: utf-8 -*-
"""x-direction half supercell with PEC/PMC symmetry planes (Table VI, Fig. 15).

Half supercell x in [0, px/2], y in [0, py]. Symmetry planes at x=0 and
x=px/2 replace the x Lattice Pair; the y Lattice Pair stays and sweeps phi_y
over [0, 2*pi] (Table IV Gamma-M range for the supercell).

  M^x_0 M^x_px/2 : both PMC -> even modes, phi_x = 0
  E^x_0 E^x_px/2 : both PEC -> odd modes,  phi_x = 2*pi
"""
import csv
import math
import os
import re
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

import hexagonal_rect as hr

ROOT = hr.ROOT
AEDT = hr.AEDT
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_symx")
LOG = os.path.join(ROOT, "hexagonal_symx.log")

DESIGN = os.environ.get("SYMX_DESIGN", "hexagonal_sym_x")
PARITY = os.environ.get("SYMX_PARITY", "probe")
MODE = os.environ.get("SYMX_MODE") or {
    "even": "mm", "odd": "ee", "em": "em", "me": "me"}.get(PARITY, "mm")
MODE_MAP = {"mm": (False, False), "ee": (True, True),
            "em": (True, False), "me": (False, True)}
SETUP = "Eigen1_SymX"
N_MODES = 12
LX2 = hr.LX / 2
LY = hr.LY
R_DISC = hr.R_DISC
H_SUB = hr.H_SUB
H_AIR = hr.H_AIR
PHASES = tuple(range(0, 361, 30))


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def left_half_disc(cx, cy, z, r, n=20):
    pts = [[cx, cy, z]]
    for i in range(n + 1):
        t = 0.5 * math.pi + math.pi * i / n
        pts.append([cx + r * math.cos(t), cy + r * math.sin(t), z])
    pts.append([cx, cy, z])
    return pts


def side_faces(obj, z_mid):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_mid) > 0.2:
            continue
        if abs(cx) < 1e-3:
            out["x0"] = face.id
        elif abs(cx - LX2) < 1e-3:
            out["xL"] = face.id
        elif abs(cy) < 1e-3:
            out["y0"] = face.id
        elif abs(cy - LY) < 1e-3:
            out["yL"] = face.id
    return out


def cap_faces(obj, z_lo, z_hi):
    out = {}
    for face in obj.faces:
        cz = float(face.center[2])
        if abs(cz - z_lo) < 1e-3:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < 1e-3:
            out["top"] = face.id
    return out


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("Lx2", "%smm" % LX2), ("Ly", "%gmm" % LY),
                        ("disc_r", "%smm" % R_DISC),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("phi_y", "0deg")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["Lx2", "Ly", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["Lx2", "Ly", "H"],
                                 name="Air", material="vacuum")
    sheets = []
    for i, (cx, cy, sx, sy) in enumerate(((0, 0, 1, 1), (0, LY, 1, -1))):
        obj = app.modeler.create_polyline(
            hr.quarter_disc(cx, cy, sx, sy, H_SUB, R_DISC),
            cover_surface=True, close_surface=True, name="Corner%d" % i)
        sheets.append(obj.name)
    obj = app.modeler.create_polyline(
        left_half_disc(LX2, LY / 2, H_SUB, R_DISC),
        cover_surface=True, close_surface=True, name="HalfDiscX")
    sheets.append(obj.name)
    app.assign_perfecte_to_sheets(sheets, name="PatchPEC")

    cs = cap_faces(sub, 0.0, H_SUB)
    ca = cap_faces(air, H_SUB, H_SUB + H_AIR)
    app.assign_perfect_e(cs["bottom"], name="Ground")
    app.assign_perfect_e(ca["top"], name="TopPEC")
    sf = side_faces(sub, H_SUB / 2)
    af = side_faces(air, H_SUB + H_AIR / 2)
    log("substrate side faces=%r air side faces=%r" % (sf, af))
    for fa, fb, name in ((sf["y0"], sf["yL"], "PairSubY"),
                         (af["y0"], af["yL"], "PairAirY")):
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1="phi_y", name=name)
    if SETUP not in app.setup_names:
        app.create_setup(SETUP, setup_type="HFSSEigen",
                         MinimumFrequency="5GHz", NumModes=N_MODES,
                         MaxDeltaFreq=1, MaximumPasses=10,
                         MinimumPasses=2, MinimumConvergedPasses=2)
    log("objects=%r" % app.modeler.object_names)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("validate=%r" % app.validate_simple())
    app.save_project(AEDT)
    return sf, af


def set_symmetry(app, sf, af, mode):
    e0, eL = MODE_MAP[mode]
    tag0 = "E" if e0 else "M"
    tagL = "E" if eL else "M"
    existing = {b.name for b in app.boundaries}
    if "SymX0_%s" % mode not in existing:
        app.assign_symmetry([sf["x0"], af["x0"]],
                            name="SymX0_%s" % mode, is_perfect_e=e0)
    if "SymXL_%s" % mode not in existing:
        app.assign_symmetry([sf["xL"], af["xL"]],
                            name="SymXL_%s" % mode, is_perfect_e=eL)
    log("%s^x_0 %s^x_px/2 applied (is_perfect_e x0=%r xL=%r)" %
        (tag0, tagL, e0, eL))


def parse_eig(text):
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tok = line.split()
        value = None
        if len(tok) >= 2:
            try:
                value = float(tok[1])
            except ValueError:
                m = re.match(r"^\s*\d+\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", line)
                if m:
                    value = float(m.group(1))
        if value is not None:
            out.append(round(value, 6))
    return out[:N_MODES]


def solve(app, parity, phase):
    app["phi_y"] = "%ddeg" % phase
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    path = os.path.join(EIG_DIR, "%s_%d.eig" % (parity, phase))
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    f = parse_eig(open(path, encoding="utf-8-sig",
                       errors="ignore").read())
    log("%s phi_y=%d solved %.1fs modes=%r" %
        (parity, phase, time.time() - t0, f[:4]))
    return f


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "HalfDiscX" not in app.modeler.object_names:
        if app.modeler.object_names:
            app.modeler.delete(list(app.modeler.object_names))
        sf, af = build(app)
    else:
        log("existing x half supercell detected")
        sf = side_faces(app.modeler["Substrate"], H_SUB / 2)
        af = side_faces(app.modeler["Air"], H_SUB + H_AIR / 2)

    if PARITY == "probe":
        set_symmetry(app, sf, af, MODE)
        solve(app, "probe_%s" % MODE, 0)
        app.save_project(AEDT)
        log("=== probe done ===")
        return

    set_symmetry(app, sf, af, MODE)
    rows = []
    for p in PHASES:
        f = solve(app, MODE, p)
        rows.append([MODE, p] + (f[:5] + [None] * (5 - len(f[:5]))))
    out = os.path.join(ROOT, "hexagonal_symx_%s.csv" % MODE)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parity", "phi_y_deg"] +
                   ["f%d_GHz" % i for i in range(1, 6)])
        for r in rows:
            w.writerow(r)
    log("wrote %s" % out)
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
