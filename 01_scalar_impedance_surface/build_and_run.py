# -*- coding: utf-8 -*-
"""Scalar impedance surface: minimal HFSS Eigenmode dispersion case.

Model: ideal isotropic impedance sheet (Rs = 0, Xs = j200 ohm/sq) at z=0,
air box above, PEC lid at z=H, two lattice pairs with a swept phase px.
HFSS Eigenmode returns f(beta) for the bound TM surface-wave mode.
Validation: beta = k0*sqrt(1+(Xs/eta0)**2)  ==>  f = c*beta/(2*pi*sqrt(1+(Xs/eta0)**2)).

Run with the PyAEDT-enabled interpreter, e.g.
  C:/Users/Verno/.workbuddy/binaries/python/envs/pyaedtmcp/Scripts/python.exe build_and_run.py
AEDT must run in GUI mode (non_graphical=False).
"""
import csv
import math
import os
import time
import traceback

# Standalone processes do not inherit AEDT's installer environment variables.
os.environ.setdefault("ANSYSEM_ROOT261", r"D:\software\ANSYS Inc\v261\AnsysEM")
os.environ.setdefault("AWP_ROOT261", r"D:\software\ANSYS Inc\v261")

from ansys.aedt.core import Hfss

ROOT = r"D:\document\Workbuddy\2026-11-07-22-48-25\scalar_impedance_eigenmode"
AEDT_FILE = os.path.join(ROOT, "scalar_impedance_eigenmode.aedt")
LOG = os.path.join(ROOT, "run.log")
CSV_FILE = os.path.join(ROOT, "dispersion.csv")
RAW_FILE = os.path.join(ROOT, "raw_reports.txt")
SVG_FILE = os.path.join(ROOT, "dispersion.svg")

C0 = 299792458.0
ETA0 = 376.730313668
XS = 200.0
P_MM = 10.0
W_MM = 2.0
H_MM = 60.0
PHASES = [50, 70, 90, 110, 130, 150, 170]
SETUP = "Eigen1"


def log(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def analytic(phase_deg):
    beta = math.radians(phase_deg) / (P_MM * 1e-3)  # rad/m
    k0 = beta / math.sqrt(1.0 + (XS / ETA0) ** 2)
    return C0 * k0 / (2.0 * math.pi) / 1e9, beta  # GHz, rad/m


def build(app, rs=0, aedt_path=AEDT_FILE):
    app.modeler.model_units = "mm"
    app["p"] = "%smm" % P_MM
    app["w"] = "%smm" % W_MM
    app["H"] = "%smm" % H_MM
    app["px"] = "90deg"
    app["Xs"] = str(XS)
    air = app.modeler.create_box([0, 0, 0], ["p", "w", "H"], name="Air", material="vacuum")
    app.modeler.create_rectangle(2, [0, 0, 0], ["p", "w"], name="ImpSheet")

    faces = {}
    for face in air.faces:
        cx, cy, cz = [float(v) for v in face.center]
        if abs(cz) < 1e-6:
            faces["bottom"] = face.id
        elif abs(cz - H_MM) < 1e-6:
            faces["top"] = face.id
        elif abs(cx) < 1e-6:
            faces["x0"] = face.id
        elif abs(cx - P_MM) < 1e-6:
            faces["xp"] = face.id
        elif abs(cy) < 1e-6:
            faces["y0"] = face.id
        elif abs(cy - W_MM) < 1e-6:
            faces["yp"] = face.id
    log("faces=%r" % faces)

    app.assign_impedance_to_sheet("ImpSheet", name="ImpBC", resistance=rs, reactance="Xs")
    app.assign_perfect_e(faces["top"], name="PEC_Top")
    app.assign_lattice_pair([faces["x0"], faces["xp"]], phase_delay="InputPhaseDelay",
                            phase_delay_param1="px", name="PairX")
    app.assign_lattice_pair([faces["y0"], faces["yp"]], phase_delay="InputPhaseDelay",
                            phase_delay_param1="0deg", name="PairY")
    setup = app.create_setup(SETUP, setup_type="HFSSEigen", MinimumFrequency="1GHz",
                             NumModes=4, MaxDeltaFreq=1, MaximumPasses=12,
                             MinimumPasses=3, MinimumConvergedPasses=2)
    log("setup=%r" % setup.props)
    log("boundaries=%r" % [b.name for b in app.boundaries])
    log("solution_type=%r validate=%r" % (app.solution_type, app.validate_simple()))
    app.save_project(aedt_path)
    log("project saved: %s" % aedt_path)


def parse_eig(text):
    """Parse the .eig table: Mode | Frequency(GHz) as 're +/- im j' | Q."""
    freqs, meta = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if len(tokens) < 2:
            continue
        try:
            f_real = float(tokens[1])
        except ValueError:
            continue
        f_imag, q_val = None, None
        try:
            f_imag = float(tokens[3])
        except (ValueError, IndexError):
            pass
        try:
            q_val = float(tokens[-1])
        except ValueError:
            pass
        freqs.append(round(f_real, 6))
        meta.append((f_imag, q_val))
    return freqs[:4], meta[:4]


def extract(app, tag):
    """Official path: Solutions.ExportEigenmodes(solution, variation, file).

    See Ansys Help "ExportEigenmodes" (HFSS Scripting, Solutions Module).
    """
    out = os.path.join(ROOT, "eig_%s.eig" % tag)
    module = app.odesign.GetModule("Solutions")
    module.ExportEigenmodes(SETUP + " : LastAdaptive", "", out)
    if not (os.path.exists(out) and os.path.getsize(out) > 10):
        raise RuntimeError("ExportEigenmodes produced no file for px=%s" % tag)
    text = open(out, encoding="utf-8-sig", errors="ignore").read()
    with open(RAW_FILE, "a", encoding="utf-8") as fh:
        fh.write("\n=== px=%s ===\n%s\n" % (tag, text))
    freqs, meta = parse_eig(text)
    q1 = meta[0][1] if meta else None
    log("exported %d bytes, freqs=%r, Q1=%r, head=%r" %
        (len(text), freqs, q1, text[:220]))
    if not freqs:
        raise RuntimeError("could not parse eigen frequencies for px=%s" % tag)
    return freqs, q1


PNG_FILE = os.path.join(ROOT, "dispersion.png")
LOSSY_AEDT = os.path.join(ROOT, "scalar_impedance_lossy.aedt")
LOSSY_CSV = os.path.join(ROOT, "lossy_result.csv")


def write_png(rows, path):
    """Same data as the SVG, rendered with matplotlib when available."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        log("matplotlib unavailable (%r); PNG skipped" % exc)
        return
    betas = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 4.4), dpi=160)
    ax.plot(betas, [r[1] for r in rows], "--", color="#1f77b4", lw=1.8,
            label="analytic beta=k0*sqrt(1+(Xs/eta0)^2)")
    ax.plot(betas, [r[3] for r in rows], "o-", color="#d62728", lw=1.8, ms=5,
            label="HFSS Eigenmode, mode 1")
    ax.set_xlabel("beta (rad/m)")
    ax.set_ylabel("f (GHz)")
    ax.set_title("Scalar impedance surface: TM surface-wave dispersion")
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    log("PNG written: %s" % path)


def lossy_check():
    """Optional branch: Rs=20 ohm/sq, one phase point, complex frequency and Q."""
    app = Hfss(project="ScalarImpedance_Lossy", design="unit_cell",
               solution_type="Eigenmode", version="2026.1",
               non_graphical=False, new_desktop=True, close_on_exit=False)
    build(app, rs=20, aedt_path=LOSSY_AEDT)
    app["px"] = "90deg"
    app.analyze_setup(SETUP, cores=4)
    freqs, q1 = extract(app, "lossy")
    app.save_project(LOSSY_AEDT)
    fa, _ = analytic(90)
    with open(LOSSY_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Rs_ohm_per_sq", "px_deg", "f_analytic_lossless_GHz",
                         "f_hfss_mode1_GHz", "Q_mode1", "all_modes_GHz"])
        writer.writerow([20, 90, round(fa, 6), freqs[0] if freqs else "",
                         "%.3e" % q1 if q1 else "",
                         " | ".join(str(v) for v in freqs)])
    log("lossy Rs=20 px=90 freqs=%r Q1=%r lossless_analytic=%.4f GHz" %
        (freqs, q1, fa))


CSV_HEADER = ["px_deg", "f_analytic_GHz", "beta_rad_per_m",
              "f_hfss_mode1_GHz", "f_hfss_mode2_GHz",
              "f_hfss_mode3_GHz", "f_hfss_mode4_GHz",
              "rel_err_pct", "Q_mode1"]


def make_row(ph, freqs, q1):
    fa, beta = analytic(ph)
    err = 100.0 * (freqs[0] - fa) / fa
    full = freqs + [None] * (4 - len(freqs))
    return ([ph, round(fa, 6), round(beta, 4)] +
            [round(v, 6) if v else "" for v in full] +
            [round(err, 3), "" if q1 is None else "%.3e" % q1])


def post_only():
    """Rebuild CSV/SVG from the .eig files already on disk; no AEDT needed."""
    rows = []
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(CSV_HEADER)
    for ph in PHASES:
        path = os.path.join(ROOT, "eig_%s.eig" % ph)
        text = open(path, encoding="utf-8-sig", errors="ignore").read()
        freqs, meta = parse_eig(text)
        q1 = meta[0][1] if meta else None
        row = make_row(ph, freqs, q1)
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(row)
        log("post-only px=%d freqs=%r f_analytic=%.4f err=%.3f%%" %
            (ph, freqs, row[1], row[7]))
        rows.append(row)
    write_svg(rows, SVG_FILE)
    write_png(rows, PNG_FILE)
    log("=== post-only done: %s / %s / %s ===" % (CSV_FILE, SVG_FILE, PNG_FILE))


def write_svg(rows, path):
    width, height = 760, 460
    x0, y0, pw, ph = 80, 390, 620, 330
    beta_max = max(r[2] for r in rows) * 1.05
    f_max = max(max([v for v in r[3:7] if isinstance(v, (int, float))] + [r[1]])
                for r in rows) * 1.1

    def sx(b):
        return x0 + pw * b / beta_max

    def sy(f):
        return y0 - ph * f / f_max

    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' %
           (width, height, width, height),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="380" y="28" text-anchor="middle" font-family="Arial" font-size="17" fill="#111">'
           'Scalar impedance surface: TM surface-wave dispersion (HFSS Eigenmode)</text>',
           '<text x="380" y="440" text-anchor="middle" font-family="Arial" font-size="12" fill="#333">'
           'beta (rad/m)</text>',
           '<text x="18" y="225" transform="rotate(-90 18 225)" text-anchor="middle" '
           'font-family="Arial" font-size="12" fill="#333">f (GHz)</text>']
    for i in range(6):
        fv = f_max * i / 5
        bv = beta_max * i / 5
        yy, xx = sy(fv), sx(bv)
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e5e5e5"/>' % (x0, yy, x0 + pw, yy))
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#e5e5e5"/>' % (xx, y0, xx, y0 - ph))
        out.append('<text x="72" y="%.1f" text-anchor="end" font-size="10" fill="#555">%.1f</text>' % (yy + 3, fv))
        out.append('<text x="%.1f" y="408" text-anchor="middle" font-size="10" fill="#555">%.0f</text>' % (xx, bv))
    out.append('<line x1="80" y1="390" x2="700" y2="390" stroke="#333"/>')
    out.append('<line x1="80" y1="60" x2="80" y2="390" stroke="#333"/>')
    # analytic line
    pts = " ".join("%.1f,%.1f" % (sx(r[2]), sy(r[1])) for r in rows)
    out.append('<polyline points="%s" fill="none" stroke="#1f77b4" stroke-width="2" '
               'stroke-dasharray="6 4"/>' % pts)
    # HFSS mode 1
    pts = " ".join("%.1f,%.1f" % (sx(r[2]), sy(r[3])) for r in rows)
    out.append('<polyline points="%s" fill="none" stroke="#d62728" stroke-width="2"/>' % pts)
    for r in rows:
        out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#d62728"/>' % (sx(r[2]), sy(r[3])))
    out.append('<text x="470" y="80" font-size="11" fill="#1f77b4" font-family="Arial">'
               'analytic beta=k0 sqrt(1+(Xs/eta0)^2)</text>')
    out.append('<text x="470" y="98" font-size="11" fill="#d62728" font-family="Arial">'
               'HFSS Eigenmode, mode 1</text>')
    out.append('</svg>')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def connect():
    """Reuse a running AEDT gRPC session when requested; otherwise launch a fresh one.

    Set AEDT_REUSE_PORT / AEDT_REUSE_PID to resume an existing session. Without them
    the script is self-contained and starts its own GUI AEDT instance.
    """
    port = int(os.environ.get("AEDT_REUSE_PORT", "0"))
    pid = int(os.environ.get("AEDT_REUSE_PID", "0"))
    if port:
        try:
            app = Hfss(project=AEDT_FILE, design="unit_cell",
                       solution_type="Eigenmode", version="2026.1",
                       non_graphical=False, new_desktop=False, close_on_exit=False,
                       port=port, aedt_process_id=(pid or None))
            log("attached to existing AEDT session on port %d" % port)
            return app
        except Exception as exc:
            log("attach failed (%r); starting a fresh AEDT session" % exc)
    return Hfss(project="ScalarImpedance_Eigen", design="unit_cell",
                solution_type="Eigenmode", version="2026.1",
                non_graphical=False, new_desktop=True, close_on_exit=False)


def main():
    log("=== start, phases=%r, Xs=%s ohm/sq, H=%s mm ===" % (PHASES, XS, H_MM))
    app = connect()
    if "Air" in app.modeler.object_names:
        if SETUP not in app.setup_names:
            raise RuntimeError("existing model has no %s setup" % SETUP)
        log("existing model detected; reuse geometry, setups=%r" % app.setup_names)
        app.save_project(AEDT_FILE)
    else:
        build(app)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerow(CSV_HEADER)

    rows = []
    for ph in PHASES:
        log("--- px=%ddeg ---" % ph)
        app["px"] = "%ddeg" % ph
        t0 = time.time()
        app.analyze_setup(SETUP, cores=4)
        log("solved in %.1fs" % (time.time() - t0))
        app.save_project(AEDT_FILE)
        freqs, q1 = extract(app, str(ph))
        row = make_row(ph, freqs, q1)
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(row)
        log("px=%d f_hfss=%r f_analytic=%.4f GHz err=%.3f%% Q1=%r" %
            (ph, freqs, row[1], row[7], q1))
        rows.append(row)

    write_svg(rows, SVG_FILE)
    write_png(rows, PNG_FILE)
    app.save_project(AEDT_FILE)
    log("=== done: %s / %s / %s ===" % (AEDT_FILE, CSV_FILE, SVG_FILE))


if __name__ == "__main__":
    try:
        mode = os.environ.get("RUN_MODE", "full")
        if mode == "post" or os.environ.get("POST_ONLY") == "1":
            post_only()
        elif mode == "lossy":
            lossy_check()
        else:
            main()
    except Exception:
        log("FATAL\n" + traceback.format_exc())
        raise
