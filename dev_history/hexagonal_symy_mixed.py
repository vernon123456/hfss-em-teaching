# -*- coding: utf-8 -*-
"""y-direction mixed symmetry planes (Fig. 15(c)(d), phi_y = pi).

  E^y_0 M^y_py/2 : y=0 PEC, y=py/2 PMC   (em)
  M^y_0 E^y_py/2 : y=0 PMC, y=py/2 PEC   (me)

Reuses the half supercell geometry and solver from hexagonal_sym.py.
Each mode uses its own design because DeleteBoundary fails on this gRPC
channel. Scan phi_x over [0, 4*pi/3] (Table IV Gamma-K1 range).
"""
import csv
import os
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

import hexagonal_sym as sy

ROOT = sy.ROOT
AEDT = sy.AEDT
DESIGN = os.environ.get("SYMY_DESIGN", "hexagonal_sym_y_em")
MODE = os.environ.get("SYMY_MODE", "em")
RUN = os.environ.get("RUN_MODE", "scan")
MODE_MAP = {"em": (True, False), "me": (False, True)}
LOG = os.path.join(ROOT, "hexagonal_symy_mixed.log")


def log(msg):
    line = "[%s] %s" % (__import__("time").strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def set_mixed(app, sf, af, mode):
    e0, eL = MODE_MAP[mode]
    tag0 = "E" if e0 else "M"
    tagL = "E" if eL else "M"
    existing = {b.name for b in app.boundaries}
    if "SymY0_%s" % mode not in existing:
        app.assign_symmetry([sf["y0"], af["y0"]], name="SymY0_%s" % mode,
                            is_perfect_e=e0)
    if "SymYL_%s" % mode not in existing:
        app.assign_symmetry([sf["yL"], af["yL"]], name="SymYL_%s" % mode,
                            is_perfect_e=eL)
    log("%s^y_0 %s^y_py/2 applied (is_perfect_e y0=%r yL=%r)" %
        (tag0, tagL, e0, eL))


def main():
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    if "HalfDisc" not in app.modeler.object_names:
        if app.modeler.object_names:
            app.modeler.delete(list(app.modeler.object_names))
        sf, af = sy.build(app)
    else:
        log("existing y half supercell detected")
        sf = sy.side_faces(app.modeler["Substrate"], sy.H_SUB / 2)
        af = sy.side_faces(app.modeler["Air"], sy.H_SUB + sy.H_AIR / 2)
    set_mixed(app, sf, af, MODE)

    if RUN == "probe":
        sy.solve(app, "probe_%s" % MODE, 0)
        app.save_project(AEDT)
        log("=== probe done ===")
        return

    rows = []
    for p in sy.PHASES:
        f = sy.solve(app, MODE, p)
        rows.append([MODE, p] + (f[:5] + [None] * (5 - len(f[:5]))))
    out = os.path.join(ROOT, "hexagonal_symy_%s.csv" % MODE)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["mode", "phi_x_deg"] +
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
