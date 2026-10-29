"""Remove the Spanish residue left by the translation of the deposit (approved by the team on 2026-10-27).

Residue found by the audit of 2026-10-27, outside bibliographic fields: Spanish ordinal indicators in the
edition of standards ("M27 4ª ed." -> "M27 4th ed."), the degree and number signs ("45 ºC", "n.º"), the words
"invasiva", "mayoritariamente", "incluye", "Inferido de", "hemocultivo(s)", "urocultivos", "neonatos",
"orofaringe", "UCI", "Cumple" and "Texto:" in extracted values and reasons, and the conjunctions "o"/"y" in lists of methods, criteria and places. Titles, journals, DOIs, labels, authors
and verbatim quotations keep their original language. The parsers of standards read the digit after the
document ("m27 ?4", "m44 3"), so the change does not alter any derived value; the rerun checks it.
Each file is archived by the caller before this script writes the corrected copy at the same path.
CSV files are rewritten cell by cell with the csv module (no type conversion); XLSX files are edited in place
with openpyxl (styles kept).
Usage: python 39_english_residue_fix_v1.py FILE [FILE ...]   (from the project root; prints the changes per file)
"""
import csv, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

KEEP = re.compile(r"title|journal|doi|pdf|label|^study$|author|evidence|quote|verbatim", re.I)
ORD = {1: "1st", 2: "2nd", 3: "3rd"}

def ordinal(m):
    n = int(m.group(1))
    return ORD.get(n, f"{n}th")

RULES = [(re.compile(r"(\d+)\s*\.?\s*ª"), ordinal),
         (re.compile(r"n\.\s*º"), "no."),
         (re.compile(r"(\d)\s*ºC"), r"\1 °C"),
         (re.compile(r"(\d+)\s*º"), ordinal),
         (re.compile(r"\bmayoritariamente invasivas?\b", re.I), "mostly invasive"),
         (re.compile(r"\binvasivas?\b", re.I), "invasive"),
         (re.compile(r"\bmayoritariamente\b", re.I), "mostly"),
         (re.compile(r"\bincluye\b", re.I), "includes"),
         (re.compile(r"\bInferido de\b"), "Inferred from"),
         (re.compile(r"\bhemocultivos\b", re.I), "blood cultures"),
         (re.compile(r"\bhemocultivo\b", re.I), "blood culture"),
         (re.compile(r"\burocultivos\b", re.I), "urine cultures"),
         (re.compile(r"\bneonatos\b", re.I), "neonates"),
         (re.compile(r"\borofaringe\b", re.I), "oropharynx"),
         (re.compile(r"\bUCI\b"), "ICU"),
         (re.compile(r"\bCumple regla\b"), "Meets rule"),
         (re.compile(r"\bCumple\b"), "Meets"),
         (re.compile(r"\bTexto:"), "Text:"),
         # (2026-10-28) residue found while preparing the second article (genotype, molecular and source fields)
         (re.compile(r"\b([Cc])lados\b"), r"\1lades"), (re.compile(r"\b([Cc])lado\b"), r"\1lade"),
         (re.compile(r"\bfilogenia bayesiana\b"), "Bayesian phylogeny"), (re.compile(r"\bfilogenia ML\b"), "ML phylogeny"),
         (re.compile(r"\bfilogenia\b"), "phylogeny"), (re.compile(r"\bprevalencia de\b"), "prevalence of"), (re.compile(r"\bGrupo (\d+) eBURST\b"), r"eBURST group \1")]
# conjunctions only in columns of methods, criteria and places, never in names of institutions
LISTS = re.compile(r"^(species_id_raw|ast_method_raw|method_raw|interp_raw|region_city_raw|identification_method|"
                   r"susceptibility_method|method|standard|region_city|Identification|Susceptibility method|"
                   r"Standard/version|criterion_raw|criterion_v)$")
CONJ = [(re.compile(r"(?<=\S) o (?=\S)"), " or "), (re.compile(r"(?<=\S) y (?=\S)"), " and ")]

def fix(s, col=""):
    for rx, rep in RULES + (CONJ if LISTS.match(col or "") else []):
        s = rx.sub(rep, s)
    return s

def fix_csv(path):
    raw = open(path, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in raw[:5000] else "\n"
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return 0
    head, n = rows[0], 0
    keep = [bool(KEEP.search(h)) for h in head]
    for r in rows[1:]:
        for i, v in enumerate(r):
            if i < len(keep) and not keep[i] and v:
                w = fix(v, head[i])
                if w != v:
                    r[i] = w; n += 1
    out = io.StringIO()
    csv.writer(out, lineterminator=nl).writerows(rows)
    open(path, "w", encoding="utf-8", newline="").write(out.getvalue())
    return n

def fix_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path)
    n = 0
    for ws in wb.worksheets:
        head = [str(c.value or "") for c in ws[1]] if ws.max_row else []
        for row in ws.iter_rows(min_row=2):
            for c in row:
                h = head[c.column - 1] if c.column - 1 < len(head) else ""
                if isinstance(c.value, str) and not KEEP.search(h):
                    w = fix(c.value, h)
                    if w != c.value:
                        c.value = w; n += 1
    wb.save(path)
    return n

def main(files):
    changes = {}
    for p in files:
        changes[p] = fix_xlsx(p) if p.endswith(".xlsx") else fix_csv(p)
        print(changes[p], p)
    print(run_log.write(__file__, [], files, cells_changed=changes))

if __name__ == "__main__":
    main(sys.argv[1:])
