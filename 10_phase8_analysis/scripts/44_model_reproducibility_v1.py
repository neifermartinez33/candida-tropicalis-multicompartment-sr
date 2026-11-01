"""Run-to-run reproducibility of the language model in full-text screening and data extraction.

A stratified random sample of the full-text screening decisions (200 reports) and a random sample of
the extracted reports with susceptibility rows (50 reports) are given again to the same model,
Claude Opus 5.5 (claude-opus-5-5), with the same instructions (File S1), and the second run is compared
with the first, as recorded in the deposited screening and extraction workbooks.

Reconstruction. The first run was made in interactive Claude Code sessions, one batch of reports per
session, and no runner script was kept. This script reproduces that procedure non-interactively:
  - the instruction is the English text of File S1 (the Spanish originals are kept by the team and are
    identified by their SHA-256 in the File S1 README); the translation preface and the table of
    original keys are removed, and the SHA-256 of the exact text sent is logged;
  - each full text is converted to text with pdftotext (the converter of the first run is not recorded),
    and the excerpt the instruction refers to (title, abstract, methods, key sentences and tables) is
    rebuilt from that text with the rules in excerpt();
  - each batch of 10 reports is run in a fresh `claude -p` session, with the instruction appended to
    the system prompt and the Read, Grep and Write tools, in the same folder layout (cribado/md,
    cribado/recorte).
The comparison therefore measures the agreement between two runs of the model with the same
instruction, not an exact replay of the first run.

Steps (each can be run alone; run is resumable, batches with an output are skipped):
  sample    draw the samples (seed 20261029) and write the batch files
  prepare   convert the PDFs and build the excerpts
  run       call the model for every pending batch of one rerun
  compare   compute the agreement between the first run and every rerun
Usage: python3 44_model_reproducibility_v1.py [sample|prepare|run|compare|all] [max_batches] [--rerun N]
       (from the project root; rerun 2 is the default, reruns 3 and later write to outputs_runN/)

Outputs (05_phase3_model_validation/reproducibility_2026-10-29/):
  sample_screening.csv, sample_extraction.csv, batches/, outputs/ (rerun 2), outputs_runN/, run_log*.csv
  agreement_screening.csv, agreement_extraction_rows.csv, agreement_summary.json
  44_model_reproducibility_v1_<step>_<ts>.json   log with MD5 checksums of inputs and outputs
"""
import hashlib, json, os, random, re, subprocess, sys
from datetime import datetime
import numpy as np
import pandas as pd

PDF_DIR = os.path.expanduser("~/EXTENCIONES/ARTICULO_COMPLETO/articulos_pdf")
FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
EXTR = "08_phase6_data_extraction/data_extraction_tropicalis.xlsx"
RIS = "06_phase4_title_abstract_screening/import/screening_reviewer_1_reviewer_2_n22203_seed1310202643.ris"
S1 = "12_documents/supplementary/file_s1_language_model_v1/full_text"
INSTR = {"screening": f"{S1}/full_text_screening_instruction_EN.md",
         "extraction": f"{S1}/data_extraction_instruction_EN.md"}
WD = "05_phase3_model_validation/reproducibility_2026-10-29"
MODEL = "claude-opus-5-5"
SEED = 20261029
N_SCREEN, N_EXTR, BATCH = 200, 50, 10
KEY_TERMS = (r"tropicalis|\bTable\b|\bCLSI\b|\bNCCLS\b|\bEUCAST\b|\bM27\b|\bM44\b|\bM60\b|\bMICs?\b|resistan|susceptib"
             r"|isolat|identif|MALDI|CHROM|Vitek|API ?20|sequenc|ERG11|MLST|clade|country|hospital|period|collected")


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_log(step, payload, inputs=(), outputs=()):
    ts = datetime.now().astimezone().strftime("%Y-%m-%dT%H%M%S")
    log = dict(script="44_model_reproducibility_v1.py", step=step, run_time=ts, **payload,
               inputs={p: md5(p) for p in inputs if os.path.exists(p)},
               outputs={os.path.relpath(p, WD): md5(p) for p in outputs if os.path.exists(p)})
    with open(os.path.join(WD, f"44_model_reproducibility_v1_{step}_{ts}.json"), "w") as fh:
        json.dump(log, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in log.items() if k not in ("inputs", "outputs")}, indent=1, ensure_ascii=False))


def stem(pdf):
    return os.path.splitext(pdf)[0]


# ---------------------------------------------------------------- sample
def sample():
    os.makedirs(os.path.join(WD, "batches"), exist_ok=True)
    ft = pd.read_excel(FT, sheet_name="All", dtype=str)
    ft = ft[ft["PDF file"].apply(lambda p: isinstance(p, str) and os.path.exists(os.path.join(PDF_DIR, p)))]
    # proportional allocation by first-run decision
    share = ft.Decision.value_counts(normalize=True)
    alloc = (share * N_SCREEN).round().astype(int)
    alloc[alloc.idxmax()] += N_SCREEN - alloc.sum()
    s = pd.concat([ft[ft.Decision == d].sample(n, random_state=SEED) for d, n in alloc.items()])
    s = s.sample(frac=1, random_state=SEED)[["ID", "PDF file", "Decision"]]
    s.columns = ["id", "pdf_file", "first_decision"]
    s.to_csv(os.path.join(WD, "sample_screening.csv"), index=False)

    st = pd.read_excel(EXTR, sheet_name="Studies", dtype=str)
    st = st[(st.decision_final == "INCLUDE") & (pd.to_numeric(st.resistance_rows, errors="coerce") > 0)]
    st = st[st["PDF file"].apply(lambda p: isinstance(p, str) and os.path.exists(os.path.join(PDF_DIR, p)))]
    e = st.sample(N_EXTR, random_state=SEED)[["ID", "PDF file", "decision_final"]]
    e.columns = ["id", "pdf_file", "screening_decision"]
    e.to_csv(os.path.join(WD, "sample_extraction.csv"), index=False)

    for task, df in (("screening", s), ("extraction", e)):
        for b in range(0, len(df), BATCH):
            items = [dict(idx=i, id=r.id, stem=stem(r.pdf_file),
                          **({"screening_decision": r.screening_decision} if task == "extraction" else {}))
                     for i, r in enumerate(df.iloc[b:b + BATCH].itertuples())]
            with open(os.path.join(WD, "batches", f"{task}_{b // BATCH + 1:03d}.json"), "w") as fh:
                json.dump(items, fh, indent=1)
    write_log("sample", dict(seed=SEED, screening=len(s), screening_by_first_decision=alloc.to_dict(),
                             extraction=len(e), batch_size=BATCH),
              inputs=(FT, EXTR), outputs=[os.path.join(WD, f) for f in ("sample_screening.csv", "sample_extraction.csv")])


# ---------------------------------------------------------------- prepare
def ris_abstracts():
    txt = open(RIS, encoding="utf-8", errors="ignore").read()
    out = {}
    for blk in re.split(r"\nER  -.*", txt):
        sid = re.search(r"\b([ORB]\d{5})\b", " ".join(re.findall(r"^(?:N1|AN)  - (.*)$", blk, re.M)))
        if sid:
            ti = re.search(r"^(?:TI|T1)  - (.*)$", blk, re.M)
            ab = re.search(r"^AB  - (.*)$", blk, re.M)
            out[sid.group(1)] = ((ti.group(1) if ti else ""), (ab.group(1) if ab else ""))
    return out


def excerpt(text, title, abstract):
    """Title and abstract from the record, the methods section (up to 6000 characters), the lines with
    key terms and the lines that look like table rows; at most 20,000 characters."""
    lines = text.splitlines()
    parts = [f"# {title}", "", "## Abstract (record)", abstract or "(not available)", ""]
    m = re.search(r"^\s*(\d[.\s]*)?(materials?\s+and\s+methods|methods|methodology|material y m[eé]todos|métodos)\s*$",
                  text, re.I | re.M)
    if m:
        parts += ["## Methods", text[m.end(): m.end() + 6000], ""]
    keys = [l.strip() for l in lines if re.search(KEY_TERMS, l, re.I) and len(l.strip()) > 20]
    tables = [l.rstrip() for l in lines if re.search(r"\S\s{3,}\S.*\s{3,}\S", l)]
    parts += ["## Key sentences"] + keys[:150] + ["", "## Table-like lines"] + tables[:200]
    return "\n".join(parts)[:20000]


def prepare():
    md, rec = os.path.join(WD, "cribado", "md"), os.path.join(WD, "cribado", "recorte")
    os.makedirs(md, exist_ok=True); os.makedirs(rec, exist_ok=True)
    ab = ris_abstracts()
    titles = pd.read_excel(FT, sheet_name="All", dtype=str).set_index("ID").Title.to_dict()
    n = 0
    for f in ("sample_screening.csv", "sample_extraction.csv"):
        for r in pd.read_csv(os.path.join(WD, f), dtype=str).itertuples():
            out_md = os.path.join(md, stem(r.pdf_file) + ".md")
            if not os.path.exists(out_md):
                subprocess.run(["pdftotext", "-q", "-layout", os.path.join(PDF_DIR, r.pdf_file), out_md])
            if not os.path.exists(out_md):  # PDF without a text layer: empty full text, as in the first run
                open(out_md, "w").close()
            text = open(out_md, errors="ignore").read()
            ti, abstract = ab.get(r.id, (titles.get(r.id, ""), ""))
            with open(os.path.join(rec, stem(r.pdf_file) + ".md"), "w") as fh:
                fh.write(excerpt(text, ti or titles.get(r.id, ""), abstract))
            n += 1
    write_log("prepare", dict(reports_prepared=n, converter="pdftotext -layout",
                              pdftotext=subprocess.run(["pdftotext", "-v"], capture_output=True, text=True).stderr.splitlines()[0]),
              inputs=(RIS, FT))


# ---------------------------------------------------------------- run
def instruction(task):
    t = open(INSTR[task], encoding="utf-8").read()
    t = t.split("\n---\n", 1)[1]                                  # drop the translation preface
    t = t.split("\n## Keys and values of the original instruction", 1)[0]
    t = re.sub(r"\nThe original asked for .*?(?=\n\n|\Z)", "", t, flags=re.S)
    return t.strip() + "\n"


def out_dir(rerun):
    """Run 1 is the first run, recorded in the screening and extraction workbooks; rerun 2 writes to
    outputs/ and rerun N >= 3 to outputs_runN/."""
    return "outputs" if rerun == 2 else f"outputs_run{rerun}"


def run(limit=None, rerun=2):
    od = out_dir(rerun)
    os.makedirs(os.path.join(WD, od), exist_ok=True)
    texts = {k: instruction(k) for k in INSTR}
    for k, t in texts.items():
        with open(os.path.join(WD, f"instruction_sent_{k}.md"), "w") as fh:
            fh.write(t)
    version = subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip()
    log_path = os.path.join(WD, "run_log.csv" if rerun == 2 else f"run_log_run{rerun}.csv")
    done = 0
    for b in sorted(os.listdir(os.path.join(WD, "batches"))):
        task = b.split("_")[0]
        out_rel = f"{od}/{b}"
        if os.path.exists(os.path.join(WD, out_rel)):
            continue
        if limit is not None and done >= limit:
            break
        verb = "Screen" if task == "screening" else "Extract the data of"
        prompt = (f"{verb} the articles listed in batches/{b} (fields idx, id, stem"
                  + (", screening_decision" if task == "extraction" else "")
                  + f"). The full texts are in cribado/md/<stem>.md and the excerpts in cribado/recorte/<stem>.md. "
                  f"Write the JSON output to {out_rel}.")
        t0 = datetime.now().astimezone().isoformat(timespec="seconds")
        r = subprocess.run(["claude", "-p", prompt, "--model", MODEL, "--append-system-prompt", texts[task],
                            "--allowedTools", "Read", "Grep", "Write", "--permission-mode", "acceptEdits",
                            "--output-format", "json"],
                           cwd=WD, capture_output=True, text=True, timeout=3600)
        meta = {}
        try:
            meta = json.loads(r.stdout)
        except json.JSONDecodeError:
            pass
        row = dict(batch=b, task=task, start=t0, end=datetime.now().astimezone().isoformat(timespec="seconds"),
                   returncode=r.returncode, output_written=os.path.exists(os.path.join(WD, out_rel)),
                   models_used="; ".join(sorted((meta.get("modelUsage") or {}).keys())),
                   cost_usd=meta.get("total_cost_usd"), claude_code=version, session_id=meta.get("session_id"))
        pd.DataFrame([row]).to_csv(log_path, mode="a", header=not os.path.exists(log_path), index=False)
        done += 1
        print(f"run {rerun} {b}: rc={r.returncode} written={row['output_written']} models={row['models_used']}", flush=True)
    write_log(f"run{rerun}", dict(rerun=rerun, batches_run=done, model_requested=MODEL, claude_code=version,
                                  instruction_sha256={k: hashlib.sha256(t.encode()).hexdigest() for k, t in texts.items()}),
              inputs=tuple(INSTR.values()), outputs=[log_path])


# ---------------------------------------------------------------- compare
def kappa(a, b, n_boot=2000):
    a, b = np.asarray(a), np.asarray(b)
    cats = sorted(set(a) | set(b))
    def k(x, y):
        po = np.mean(x == y)
        pe = sum(np.mean(x == c) * np.mean(y == c) for c in cats)
        return (po - pe) / (1 - pe) if pe < 1 else 1.0
    rng = np.random.default_rng(SEED)
    boots = [k(a[i], b[i]) for i in (rng.integers(0, len(a), len(a)) for _ in range(n_boot))]
    return round(float(np.mean(a == b)), 4), round(float(k(a, b)), 3), [round(float(q), 3) for q in np.percentile(boots, [2.5, 97.5])]


def fleiss(table):
    """Fleiss' kappa for a list of rows, each the categories given by every run to one report."""
    cats = sorted({c for row in table for c in row})
    n, m = len(table), len(table[0])
    counts = np.array([[row.count(c) for c in cats] for row in table], dtype=float)
    p_j = counts.sum(0) / (n * m)
    p_i = ((counts ** 2).sum(1) - m) / (m * (m - 1))
    pe = (p_j ** 2).sum()
    return round(float((p_i.mean() - pe) / (1 - pe)), 3) if pe < 1 else 1.0


def reruns():
    """Reruns with at least one output batch, as {rerun: directory}."""
    out = {}
    for k in range(2, 10):
        d = os.path.join(WD, out_dir(k))
        if os.path.isdir(d) and any(f.endswith(".json") for f in os.listdir(d)):
            out[k] = d
    return out


def load_outputs(task, rerun=2):
    rows, d = [], os.path.join(WD, out_dir(rerun))
    for b in sorted(os.listdir(d)):
        if b.startswith(task):
            try:
                rows += json.load(open(os.path.join(d, b)))
            except (json.JSONDecodeError, OSError):
                print(f"unreadable output: {out_dir(rerun)}/{b}")
    return rows


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def compare():
    """Run 1 against every rerun, the reruns against each other, and, with three or more runs, Fleiss'
    kappa and the share of reports with the same screening decision in every run."""
    runs = reruns()
    ft = pd.read_excel(FT, sheet_name="All", dtype=str).set_index("ID")
    s = pd.read_csv(os.path.join(WD, "sample_screening.csv"), dtype=str).rename(columns={"first_decision": "decision_1"})
    s["ma_1"] = s.id.map(lambda i: str(ft.loc[i, "Meta-analysis"]).upper())
    s["reason_1"] = s.id.map(lambda i: (re.findall(r"EC\d+", str(ft.loc[i, "Main reason"])) or [""])[0])
    for k in runs:
        o = {x["id"]: x for x in load_outputs("screening", k)}
        s[f"decision_{k}"] = s.id.map(lambda i: str(o[i].get("decision", "")).upper() if i in o else None)
        s[f"ma_{k}"] = s.id.map(lambda i: str(o[i].get("meta_analysis", "")).upper() if i in o else None)
        s[f"reason_{k}"] = s.id.map(lambda i: (re.findall(r"EC\d+", str(o[i].get("main_reason", ""))) or [""])[0] if i in o else None)
    s.to_csv(os.path.join(WD, "agreement_screening.csv"), index=False)
    all_runs = [1] + list(runs)
    pairs = {}
    for i, a in enumerate(all_runs):
        for b in all_runs[i + 1:]:
            x = s.dropna(subset=[f"decision_{a}", f"decision_{b}"])
            both_ex = x[(x[f"decision_{a}"] == "EXCLUDE") & (x[f"decision_{b}"] == "EXCLUDE")]
            pairs[f"run{a}_vs_run{b}"] = dict(
                reports=len(x),
                decision_3_categories=dict(zip(("agreement", "kappa", "kappa_95ci"), kappa(x[f"decision_{a}"], x[f"decision_{b}"]))),
                include_vs_not=dict(zip(("agreement", "kappa", "kappa_95ci"),
                                        kappa(x[f"decision_{a}"] == "INCLUDE", x[f"decision_{b}"] == "INCLUDE"))),
                meta_analysis=dict(zip(("agreement", "kappa", "kappa_95ci"), kappa(x[f"ma_{a}"], x[f"ma_{b}"]))),
                main_reason_when_both_excluded=dict(n=len(both_ex), agreement=round(float((both_ex[f"reason_{a}"] == both_ex[f"reason_{b}"]).mean()), 4) if len(both_ex) else None),
                crosstab={f"{p}|{q}": int(n) for (p, q), n in x.groupby([f"decision_{a}", f"decision_{b}"]).size().items()})
    summary = dict(runs=all_runs, screening=dict(reports_sampled=N_SCREEN, pairs=pairs))
    if len(all_runs) >= 3:
        x = s.dropna(subset=[f"decision_{k}" for k in all_runs])
        tab = [[r[f"decision_{k}"] for k in all_runs] for _, r in x.iterrows()]
        summary["screening"]["all_runs"] = dict(reports=len(x), fleiss_kappa=fleiss(tab),
                                                same_decision_in_every_run=round(float(np.mean([len(set(t)) == 1 for t in tab])), 4))

    st = pd.read_excel(EXTR, sheet_name="Studies", dtype=str).set_index("ID")
    res = pd.read_excel(EXTR, sheet_name="Resistance", dtype=str)
    e = pd.read_csv(os.path.join(WD, "sample_extraction.csv"), dtype=str)
    key = lambda c, a: (str(c).strip().upper(), str(a).strip().lower())
    rows, ext = [], {}
    for k in runs:
        second = {o["id"]: o for o in load_outputs("extraction", k)}
        n_trop, comp, n = [], [], 0
        for i in e.id:
            if i not in second:
                continue
            n += 1
            o = second[i]; so = o.get("study") or {}
            n_trop.append(num(st.loc[i, "n_tropicalis_total"]) == num(so.get("n_tropicalis_total")))
            c1 = set(re.findall(r"C[1-6]", str(st.loc[i, "compartments"])))
            comp.append(c1 == set(re.findall(r"C[1-6]", json.dumps(so.get("compartments")))))
            r1 = {key(r.compartment, r.antifungal): r for r in res[res.ID == i].itertuples()}
            r2 = {key(r.get("compartment"), r.get("antifungal")): r for r in (o.get("resistance") or [])}
            for k_ in sorted(set(r1) | set(r2)):
                a, b = r1.get(k_), r2.get(k_)
                row = dict(rerun=k, id=i, compartment=k_[0], antifungal=k_[1], in_first=a is not None, in_second=b is not None)
                if a is not None and b is not None:
                    for f in ("n_tested", "n_S", "n_SDD_I", "n_R", "n_NWT"):
                        x_, y_ = num(getattr(a, f)), num(b.get(f))
                        row[f"same_{f}"] = bool((np.isnan(x_) and np.isnan(y_)) or x_ == y_)
                    row["same_all_counts"] = all(row[f"same_{f}"] for f in ("n_tested", "n_S", "n_SDD_I", "n_R", "n_NWT"))
                rows.append(row)
        rr = pd.DataFrame([r for r in rows if r["rerun"] == k])
        paired = rr[rr.in_first & rr.in_second] if len(rr) else rr
        ext[f"run1_vs_run{k}"] = dict(
            reports=n, same_n_tropicalis=int(sum(n_trop)), same_compartments=int(sum(comp)),
            rows_first=int(rr.in_first.sum()) if len(rr) else 0, rows_second=int(rr.in_second.sum()) if len(rr) else 0,
            rows_in_both=len(paired),
            rows_same_n_tested=int(paired.same_n_tested.sum()) if len(paired) else 0,
            rows_same_n_R=int(paired.same_n_R.sum()) if len(paired) else 0,
            rows_same_all_counts=int(paired.same_all_counts.sum()) if len(paired) else 0)
    pd.DataFrame(rows).to_csv(os.path.join(WD, "agreement_extraction_rows.csv"), index=False)
    summary["extraction"] = dict(reports_sampled=N_EXTR, pairs=ext)
    with open(os.path.join(WD, "agreement_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    write_log("compare", summary, inputs=(FT, EXTR),
              outputs=[os.path.join(WD, f) for f in ("agreement_screening.csv", "agreement_extraction_rows.csv", "agreement_summary.json")])


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(WD, exist_ok=True)
    random.seed(SEED)
    rest = sys.argv[2:]
    rerun = 2
    if "--rerun" in rest:
        i = rest.index("--rerun"); rerun = int(rest[i + 1]); rest = rest[:i] + rest[i + 2:]
    limit = int(rest[0]) if rest else None
    for name, fn in (("sample", sample), ("prepare", prepare), ("run", lambda: run(limit, rerun)), ("compare", compare)):
        if step in (name, "all"):
            fn()


if __name__ == "__main__":
    main()
