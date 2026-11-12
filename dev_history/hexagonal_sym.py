# -*- coding: utf-8 -*-
"""Even/odd modes via PEC/PMC symmetry planes, following Table VI / Fig. 15
of Jimenez-Suarez et al., IEEE TMTT 73(9), 2025.

A half supercell (y in [0, py/2]) replaces the y-periodic Lattice Pair with
two symmetry planes at y=0 and y=py/2:
  M^y_0 M^y_py/2 : both PMC  -> even modes (phi_y = 0)
  E^y_0 E^y_py/2 : both PEC  -> odd modes  (phi_y = 2*pi)
The x-direction keeps a Lattice Pair with phase phi_x for the Gamma-K1 path.
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
import hexagonal_ibz as ibz

ROOT = hr.ROOT
AEDT = hr.AEDT
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_sym")
LOG = os.path.join(ROOT, "hexagonal_sym.log")
OUT_CSV = os.path.join(ROOT, "hexagonal_sym.csv")
COMPARE_PNG = os.path.join(ROOT, "hexagonal_sym_compare.png")

DESIGN = os.environ.get("SYM_DESIGN", "hexagonal_sym")
ONLY_PARITY = os.environ.get("SYM_PARITY", "both")
SETUP = "Eigen1_Sym"
N_MODES = 12
LX = hr.LX
LY2 = hr.LY / 2
R_DISC = hr.R_DISC
H_SUB = hr.H_SUB
H_AIR = hr.H_AIR
PHASES = (0, 30, 60, 90, 120, 150, 180, 210, 240)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def half_disc(cx, cy, z, r, n=20):
    pts = [[cx, cy, z]]
    for i in range(n + 1):
        t = math.pi + math.pi * i / n
        pts.append([cx + r * math.cos(t), cy + r * math.sin(t), z])
    pts.append([cx, cy, z])
    return pts


def side_faces(obj, z_mid):
    out = {}
    for face in obj.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz - z_mid) > 0.2:
            continue
        if abs(cy) < 1e-3:
            out["y0"] = face.id
        elif abs(cy - LY2) < 1e-3:
            out["yL"] = face.id
        elif abs(cx) < 1e-3:
            out["x0"] = face.id
        elif abs(cx - LX) < 1e-3:
            out["xL"] = face.id
        elif abs(cz - z_mid) <= 0.2 and cy < 0.2:
            pass
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
    for name, value in (("Lx", "%smm" % LX), ("Ly2", "%gmm" % LY2),
                        ("disc_r", "%smm" % R_DISC),
                        ("hs", "%smm" % H_SUB), ("H", "%smm" % H_AIR),
                        ("phi_x", "0deg")):
        app[name] = value
    mat = app.materials.add_material("Sub22")
    mat.permittivity = 2.2
    sub = app.modeler.create_box([0, 0, 0], ["Lx", "Ly2", "hs"],
                                 name="Substrate", material="Sub22")
    air = app.modeler.create_box([0, 0, "hs"], ["Lx", "Ly2", "H"],
                                 name="Air", material="vacuum")
    sheets = []
    for i, (cx, cy, sx, sy) in enumerate(((0, 0, 1, 1), (LX, 0, -1, 1))):
        obj = app.modeler.create_polyline(
            hr.quarter_disc(cx, cy, sx, sy, H_SUB, R_DISC),
            cover_surface=True, close_surface=True, name="Corner%d" % i)
        sheets.append(obj.name)
    obj = app.modeler.create_polyline(
        half_disc(LX / 2, LY2, H_SUB, R_DISC),
        cover_surface=True, close_surface=True, name="HalfDisc")
    sheets.append(obj.name)
    app.assign_perfecte_to_sheets(sheets, name="PatchPEC")

    cs = cap_faces(sub, 0.0, H_SUB)
    ca = cap_faces(air, H_SUB, H_SUB + H_AIR)
    app.assign_perfect_e(cs["bottom"], name="Ground")
    app.assign_perfect_e(ca["top"], name="TopPEC")

    sf = side_faces(sub, H_SUB / 2)
    af = side_faces(air, H_SUB + H_AIR / 2)
    log("substrate side faces=%r air side faces=%r" % (sf, af))
    for fa, fb, name in ((sf["x0"], sf["xL"], "PairSubX"),
                         (af["x0"], af["xL"], "PairAirX")):
        app.assign_lattice_pair([fa, fb], phase_delay="InputPhaseDelay",
                                phase_delay_param1="phi_x", name=name)
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


def set_symmetry(app, sf, af, is_perfect_e):
    """Replace the two y-faces with PMC (even) or PEC (odd) symmetry planes."""
    tag = "E" if is_perfect_e else "M"
    app.assign_symmetry([sf["y0"], af["y0"]], name="SymY0_%s" % tag,
                        is_perfect_e=is_perfect_e)
    app.assign_symmetry([sf["yL"], af["yL"]], name="SymYL_%s" % tag,
                        is_perfect_e=is_perfect_e)
    log("%s^y_0 %s^y_py/2 applied (is_perfect_e=%r)" %
        (tag, tag, is_perfect_e))


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
    app["phi_x"] = "%ddeg" % phase
    t0 = time.time()
    app.analyze_setup(SETUP, cores=4)
    path = os.path.join(EIG_DIR, "%s_%d.eig" % (parity, phase))
    app.odesign.GetModule("Solutions").ExportEigenmodes(
        SETUP + " : LastAdaptive", "", path)
    f = parse_eig(open(path, encoding="utf-8-sig",
                       errors="ignore").read())
    log("%s phi_x=%d solved %.1fs modes=%r" %
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
    if "HalfDisc" not in app.modeler.object_names:
        app.modeler.delete(list(app.modeler.object_names)) \
            if app.modeler.object_names else None
        sf, af = build(app)
    else:
        log("existing half supercell detected")
        sf = side_faces(app.modeler["Substrate"], H_SUB / 2)
        af = side_faces(app.modeler["Air"], H_SUB + H_AIR / 2)

    rows = []
    for parity, is_e in (("even", False), ("odd", True)):
        if ONLY_PARITY not in ("both", parity):
            continue
        set_symmetry(app, sf, af, is_e)
        for p in PHASES:
            f = solve(app, parity, p)
            rows.append([parity, p] + (f[:5] + [None] * (5 - len(f[:5]))))
    out_csv = os.path.join(ROOT, "hexagonal_sym_%s.csv" % ONLY_PARITY)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["parity", "phi_x_deg"] +
                   ["f%d_GHz" % i for i in range(1, 6)])
        for r in rows:
            w.writerow(r)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.6, 4.6), dpi=170)
        for parity, color in (("even", "#185FA5"), ("odd", "#d62728")):
            pts = [r for r in rows if r[0] == parity]
            xs = [r[1] for r in pts]
            for idx in (1, 2):
                ys = [r[1 + idx] for r in pts if r[1 + idx] is not None]
                ax.plot(xs[:len(ys)], ys, "o-", ms=3.5, lw=1.3,
                        color=color,
                        label="%s mode%d" % (parity, idx) if idx == 1 else None)
        ax.set_xlabel("phi_x (deg), Gamma-K1 path")
        ax.set_ylabel("f (GHz)")
        ax.set_title("Even (M-M) and odd (E-E) symmetry-plane modes")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(COMPARE_PNG)
        plt.close(fig)
        log("compare plot written")
    except Exception as exc:
        log("plot failed: %r" % exc)
    app.save_project(AEDT)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
