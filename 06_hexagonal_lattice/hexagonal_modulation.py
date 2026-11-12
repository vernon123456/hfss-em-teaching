# -*- coding: utf-8 -*-
"""Two-site dimerization in the hexagonal rectangular supercell.

The centre disc radius is an AEDT expression disc_r = 1.2mm*(1+M); the four
corner quarter-disc sheets are fixed polylines, so sweeping M makes the two
lattice sites inequivalent. An Optimetrics sweep over M and phi_y gives the
first two eigenfrequencies at each point; their difference is tracked.

This is a dimerization, not the 8-cell sinusoidal gap modulation of the
square-patch baseline, so the comparison is qualitative only.
"""
import csv
import os
import re
import time
import traceback

os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\tensor_patch"
AEDT = os.path.join(ROOT, "tensor_patch.aedt")
EIG_DIR = os.path.join(ROOT, "eig_hexagonal_modulation")
LOG = os.path.join(ROOT, "hexagonal_modulation.log")
OUT_CSV = os.path.join(ROOT, "hexagonal_modulation.csv")
GAP_CSV = os.path.join(ROOT, "hexagonal_modulation_gap.csv")
GAP_PNG = os.path.join(ROOT, "hexagonal_modulation_gap.png")

DESIGN = "hexagonal"
SETUP = "Eigen1_IBZ"
PARAM_SETUP = "SweepModulation"
M_VALUES = (0.0, 0.1, 0.2, 0.3)
PHI_VALUES = (0, 90, 180)


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


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
    return out[:4]


def main():
    os.makedirs(EIG_DIR, exist_ok=True)
    lock = AEDT + ".lock"
    if os.path.exists(lock):
        os.remove(lock)
    app = Hfss(project=AEDT, design=DESIGN, solution_type="Eigenmode",
               version="2026.1", non_graphical=False, new_desktop=True,
               close_on_exit=False)
    for name, value in (("M", "0"), ("phi_x", "0deg")):
        app[name] = value
    app["disc_r"] = "1.2mm*(1+M)"
    log("disc_r -> %r; M=%r" % (app["disc_r"], app["M"]))

    if PARAM_SETUP in [s.name for s in app.parametrics.setups]:
        app.parametrics.delete(PARAM_SETUP)
    setup = app.parametrics.add(
        "M", M_VALUES[0], M_VALUES[-1], M_VALUES[1] - M_VALUES[0],
        variation_type="LinearStep",
        solution=SETUP + " : LastAdaptive", name=PARAM_SETUP)
    setup.add_variation("phi_y", PHI_VALUES[0], PHI_VALUES[-1],
                        PHI_VALUES[1] - PHI_VALUES[0], units="deg",
                        variation_type="LinearStep")
    log("sweep props=%r" % setup.props["Sweeps"])

    sol = app.odesign.GetModule("Solutions")
    before = set(sol.ListVariations(SETUP + " : LastAdaptive"))
    t0 = time.time()
    setup.analyze()
    log("sweep solved in %.1fs" % (time.time() - t0))
    app.save_project(AEDT)
    keys = [k for k in sol.ListVariations(SETUP + " : LastAdaptive")
            if k not in before]
    log("new variations: %d" % len(keys))

    rows = []
    for idx, key in enumerate(keys):
        path = os.path.join(EIG_DIR, "var%02d.eig" % idx)
        try:
            sol.ExportEigenmodes(SETUP + " : LastAdaptive", key, path)
            freqs = parse_eig(open(path, encoding="utf-8-sig",
                                   errors="ignore").read())
        except Exception as exc:
            log("export %s failed: %r" % (key, exc))
            freqs = []
        mm = re.search(r"M='([^']+)'", key)
        pp = re.search(r"phi_y='([^']+)'", key)
        mval = float(mm.group(1)) if mm else ""
        pval = float(pp.group(1).replace("deg", "")) if pp else ""
        gap = (freqs[1] - freqs[0]) if len(freqs) >= 2 else None
        rows.append([key, mval, pval] + freqs +
                    [None] * (4 - len(freqs)) + [gap])
        log("var%02d M=%s phi_y=%s f1=%s f2=%s gap=%s" %
            (idx, mval, pval,
             freqs[0] if freqs else "n/a",
             freqs[1] if len(freqs) > 1 else "n/a",
             "%.6f" % gap if gap is not None else "n/a"))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["variation", "M", "phi_y_deg", "f1_GHz", "f2_GHz",
                    "f3_GHz", "f4_GHz", "gap_GHz"])
        for r in rows:
            w.writerow(r)

    bands = []
    with open(GAP_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["M", "phi_y_deg", "f1_GHz", "f2_GHz", "gap_GHz"])
        for phi in PHI_VALUES:
            for m in M_VALUES:
                cand = [r for r in rows if r[1] == m and r[2] == phi
                        and r[-1] is not None]
                if not cand:
                    continue
                r = cand[0]
                w.writerow([m, phi, r[3], r[4], round(r[-1], 6)])
                bands.append((phi, m, r[-1]))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=165)
        for phi in PHI_VALUES:
            pts = [(m, g) for p, m, g in bands if p == phi]
            if not pts:
                continue
            pts.sort()
            ax.plot([p[0] for p in pts], [p[1] for p in pts], "o-",
                    ms=5, lw=1.6, label="phi_y=%d deg" % phi)
        ax.set_xlabel("modulation depth M")
        ax.set_ylabel("lowest-branch gap f2-f1 (GHz)")
        ax.set_title("Hexagonal supercell dimerization gap")
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(GAP_PNG)
        plt.close(fig)
        log("gap plot written")
    except Exception as exc:
        log("plot failed: %r" % exc)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
