# -*- coding: utf-8 -*-
"""Step 2 probe: can a DrivenModal HFSS unit cell produce valid S-parameters?

Official constraints (Ansys Help, HFSS Floquet Ports Introduction):
  - Floquet ports only in modal (DrivenModal) projects
  - boundaries adjacent to a Floquet port must be linked boundaries
  - fast frequency sweep is not supported; Discrete/Interpolating only
This probe builds a rectangular supercell with four Lattice Pairs and one
Floquet port on top, solves a discrete sweep, and exports Touchstone S11.

It does NOT yet invert gamma = alpha + j beta. That is step 4.
"""
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
LOG = os.path.join(ROOT, "hexagonal_driven_probe.log")
TOUCHSTONE = os.path.join(ROOT, "hexagonal_driven_probe.s1p")

DESIGN = "hexagonal_driven_probe"
SETUP = "DrivenSetup"
SWEEP = "DiscreteSweep"
LX, LY = hr.LX, hr.LY
H_SUB = hr.H_SUB
H_AIR = 10.0
R_DISC = hr.R_DISC


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def cap_face(obj, z_value):
    for face in obj.faces:
        if abs(float(face.center[2]) - z_value) < 1e-3:
            return face.id
    return None


def side_faces(obj, z_mid):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_mid) > 0.2:
            continue
        if abs(cx) < 1e-3:
            out["x0"] = face.id
        elif abs(cx - LX) < 1e-3:
            out["xL"] = face.id
        elif abs(cy) < 1e-3:
            out["y0"] = face.id
        elif abs(cy - LY) < 1e-3:
            out["yL"] = face.id
    return out


def quarter(cx, cy, sx, sy, z, r, n=14):
    pts = [[cx, cy, z]]
    for i in range(n + 1):
        t = 0.5 * math.pi * i / n
        pts.append([cx + sx * r * math.cos(t), cy + sy * r * math.sin(t), z])
    pts.append([cx, cy, z])
    return pts


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("Lx", "%smm" % LX), ("Ly", "%gmm" % LY),
                        ("disc_r", "%smm" % R_DISC),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("phi_x", "0deg"), ("phi_y", "0deg")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["Lx", "Ly", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["Lx", "Ly", "H"],
                                 name="Air", material="vacuum")
    sheets = []
    app.modeler.create_circle(2, ["Lx/2", "Ly/2", "hs"], "disc_r", name="Disc")
    sheets.append("Disc")
    for i, (cx, cy, sx, sy) in enumerate(((0, 0, 1, 1), (LX, 0, -1, 1),
                                          (0, LY, 1, -1), (LX, LY, -1, -1))):
        obj = app.modeler.create_polyline(
            quarter(cx, cy, sx, sy, H_SUB, R_DISC),
            cover_surface=True, close_surface=True, name="Corner%d" % i)
        sheets.append(obj.name)
    app.assign_perfecte_to_sheets(sheets, name="PatchPEC")
    app.assign_perfect_e(cap_face(sub, 0.0), name="Ground")

    sf = side_faces(sub, H_SUB / 2)
    af = side_faces(air, H_SUB + H_AIR / 2)
    log("substrate side faces=%r air side faces=%r" % (sf, af))
    for fa, fb, var, name in ((sf["x0"], sf["xL"], "phi_x", "PairSubX"),
                              (af["x0"], af["xL"], "phi_x", "PairAirX"),
                              (sf["y0"], sf["yL"], "phi_y", "PairSubY"),
                              (af["y0"], af["yL"], "phi_y", "PairAirY")):
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1=var, name=name)

    ztop = H_SUB + H_AIR
    top = cap_face(air, ztop)
    app.create_floquet_port(
        top,
        lattice_origin=["0mm", "0mm", "%gmm" % ztop],
        lattice_a_end=["%gmm" % LX, "0mm", "%gmm" % ztop],
        lattice_b_end=["0mm", "%gmm" % LY, "%gmm" % ztop],
        modes=2, name="FloquetTop", renormalize=True)
    log("floquet port assigned on face %s at z=%gmm" % (top, ztop))

    app.create_setup(SETUP, setup_type="HFSSDriven",
                     Frequency="17GHz", MaxDeltaS=0.02,
                     MaximumPasses=10, MinimumPasses=2)
    app.create_linear_count_sweep(SETUP, "GHz", 15.0, 19.0, 9,
                                  name=SWEEP, sweep_type="Discrete",
                                  save_fields=False)
    log("objects=%r" % app.modeler.object_names)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("floquet port boundary present=%r" %
        ("FloquetTop" in [b.name for b in app.boundaries]))
    log("validate=%r" % app.validate_simple())
    app.save_project(AEDT)


def parse_touchstone(path):
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path, encoding="utf-8-sig", errors="ignore"):
        s = line.strip()
        if not s or s.startswith(("!", "#", "[")):
            continue
        t = s.split()
        try:
            vals = [float(x) for x in t]
        except ValueError:
            continue
        if len(vals) >= 3:
            f_hz = vals[0]
            s11 = complex(vals[1], vals[2])
            rows.append((f_hz / 1e9, abs(s11)))
    return rows


def main():
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Modal",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Disc" not in app.modeler.object_names:
        if app.modeler.object_names:
            app.modeler.delete(list(app.modeler.object_names))
        build(app)
    else:
        log("existing driven probe design detected")
    t0 = time.time()
    ok = app.analyze_setup(SETUP, cores=4)
    log("analyze_setup returned %r in %.1fs" % (ok, time.time() - t0))
    out = app.export_touchstone(setup=SETUP, sweep=SWEEP,
                                output_file=TOUCHSTONE)
    log("touchstone -> %r" % out)
    path = out if isinstance(out, str) and os.path.exists(out) else TOUCHSTONE
    rows = parse_touchstone(path)
    log("S11 points=%d" % len(rows))
    for f, mag in rows[:5]:
        log("  f=%.3f GHz |S11|=%.6f" % (f, mag))
    violation = [r for r in rows if r[1] > 1.0001]
    log("energy-conservation violations (|S11|>1): %d" % len(violation))
    app.save_project(AEDT)
    log("=== probe done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
