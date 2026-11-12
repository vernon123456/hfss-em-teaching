# -*- coding: utf-8 -*-
"""Triangular lattice in a rectangular supercell with orthogonal Lattice Pairs.

Supercell Lx = a, Ly = sqrt(3)*a contains two lattice sites: one full disc at
the centre plus four quarter discs at the corners (periodic images of one
disc). This keeps the x/y boundaries orthogonal, reusing the 4-pair
Primary/Secondary setup that is known to solve in this workspace.

Phases: phi_x = k_x * Lx, phi_y = k_y * Ly. The supercell BZ is folded, so
mode ordering must be tracked by frequency continuity.
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

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
AEDT = os.path.join(ROOT, "tensor_patch.aedt")
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_rect")
LOG = os.path.join(ROOT, "hexagonal_rect.log")

DESIGN = "hexagonal"
SETUP = "Eigen1_Rect"
N_MODES = 8
A_MM = 3.0
LX = A_MM
LY = math.sqrt(3.0) * A_MM
R_DISC = 1.2
H_SUB = 1.57
H_AIR = 30.0


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def quarter_disc(cx, cy, sx, sy, z, r, n=14):
    pts = [[cx, cy, z]]
    for i in range(n + 1):
        t = 0.5 * math.pi * i / n
        pts.append([cx + sx * r * math.cos(t), cy + sy * r * math.sin(t), z])
    pts.append([cx, cy, z])
    return pts


def box_faces(obj, z_lo, z_hi):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_lo) < 1e-6:
            out["bottom"] = face.id
        elif abs(cz - z_hi) < 1e-6:
            out["top"] = face.id
        elif abs(cx) < 1e-6:
            out["x0"] = face.id
        elif abs(cx - LX) < 1e-3:
            out["xL"] = face.id
        elif abs(cy) < 1e-3:
            out["y0"] = face.id
        elif abs(cy - LY) < 1e-3:
            out["yL"] = face.id
    return out


def clear_design(app):
    # Deleting all objects also removes boundaries bound to their faces.
    objs = list(app.modeler.object_names)
    if objs:
        app.modeler.delete(objs)
    log("cleared %d objects" % len(objs))


def build(app):
    app.modeler.model_units = "mm"
    for name, value in (("a", "%smm" % A_MM), ("Lx", "%smm" % LX),
                        ("Ly", "%gmm" % LY), ("disc_r", "%smm" % R_DISC),
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
    app.modeler.create_circle(2, ["Lx/2", "Ly/2", "hs"], "disc_r",
                              name="Disc")
    sheets.append("Disc")
    corners = ((0, 0, 1, 1), (LX, 0, -1, 1),
               (0, LY, 1, -1), (LX, LY, -1, -1))
    for i, (cx, cy, sx, sy) in enumerate(corners):
        pts = quarter_disc(cx, cy, sx, sy, H_SUB, R_DISC)
        obj = app.modeler.create_polyline(
            pts, cover_surface=True, close_surface=True,
            name="Corner%d" % i)
        sheets.append(obj.name)
    app.assign_perfecte_to_sheets(sheets, name="PatchPEC")

    sf = box_faces(sub, 0.0, H_SUB)
    af = box_faces(air, H_SUB, H_SUB + H_AIR)
    log("substrate faces=%r air faces=%r" % (sf, af))
    app.assign_perfect_e(sf["bottom"], name="Ground")
    app.assign_perfect_e(af["top"], name="TopPEC")
    pairs = ((sf["x0"], sf["xL"], "phi_x", "PairSubX"),
             (af["x0"], af["xL"], "phi_x", "PairAirX"),
             (sf["y0"], sf["yL"], "phi_y", "PairSubY"),
             (af["y0"], af["yL"], "phi_y", "PairAirY"))
    for fa, fb, var, name in pairs:
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1=var, name=name)
    if SETUP not in app.setup_names:
        app.create_setup(SETUP, setup_type="HFSSEigen",
                         MinimumFrequency="5GHz", NumModes=N_MODES,
                         MaxDeltaFreq=1, MaximumPasses=10,
                         MinimumPasses=2, MinimumConvergedPasses=2)
    log("objects=%r" % app.modeler.object_names)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("validate=%r" % app.validate_simple())
    app.save_project(AEDT)


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


def eigen(app, tag):
    path = os.path.join(EIG_DIR, tag + ".eig")
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    return parse_eig(open(path, encoding="utf-8-sig",
                          errors="ignore").read())


def solve(app, px, py, tag):
    app["phi_x"] = "%gdeg" % px
    app["phi_y"] = "%gdeg" % py
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    f = eigen(app, tag)
    log("phi_x=%g phi_y=%g solved %.1fs modes=%r" %
        (px, py, time.time() - t0, f[:5]))
    return f


def run_dispersion(app):
    rows = []
    for py in (0, 30, 60, 90, 120, 150, 180):
        f = solve(app, 0, py, "gm_y%d" % py)
        rows.append([0, py] + f[:3] + [None] * (3 - len(f[:3])))
    with open(os.path.join(ROOT, "hexagonal_rect_dispersion.csv"), "w",
              newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["phi_x_deg", "phi_y_deg", "f1_GHz", "f2_GHz", "f3_GHz"])
        for r in rows:
            w.writerow(r)


def main():
    mode = os.environ.get("RUN_MODE", "probe")
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "Corner0" not in app.modeler.object_names:
        clear_design(app)
        build(app)
    else:
        log("existing rectangular supercell detected")

    if mode == "dispersion":
        run_dispersion(app)
    else:
        solve(app, 0, 0, "probe")
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
