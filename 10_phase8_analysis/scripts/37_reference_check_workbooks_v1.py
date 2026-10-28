"""Round 3 (reference-list check): screening and extraction workbooks in the format of the deposited ones.

Inputs:
  model screening output (r3_00.json) and extraction output (r3_e00.json), written by the language model with the
  frozen phase 5 and phase 6 instructions (Spanish free text, as in those phases);
  a translation file (JSON) with the English version of every Spanish free-text value, keyed by report and field,
  written for this round with the method used to translate the rest of the project;
  the candidate registry of 36_reference_check_retrieve_v1.py;
  the deposited screening workbook, to place the B reports in the EC12 groups (same country and same normalised
  programme or institution as an included report).
Outputs (never overwritten):
  07_phase5_full_text_screening/reference_check_2026-10-27/full_text_screening_r3_v1_<date-time>.xlsx
      sheets All (columns of full_text_screening.xlsx) and Possible duplicates EC12
  08_phase6_data_extraction/reference_check_2026-10-27/data_extraction_r3_v1_<date-time>.xlsx
      sheets Studies, Resistance, Molecular, Genotype, Dynamics, Clade 4 (columns of data_extraction_tropicalis.xlsx)
Nothing here is verified: the B reports enter the FINAL dataset only through the round 3 verification workbook.
Usage: python 37_reference_check_workbooks_v1.py SCREENING_JSON EXTRACTION_JSON TRANSLATIONS_JSON   (from the project root)
"""
import collections, glob, json, os, re, sys, datetime
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_log  # noqa: E402

FT = "07_phase5_full_text_screening/full_text_screening.xlsx"
REG = "07_phase5_full_text_screening/reference_check_2026-10-27"
EXT = "08_phase6_data_extraction/reference_check_2026-10-27"
CODE = {"INCLUIR": "INCLUDE", "EXCLUIR": "EXCLUDE", "DUDOSO": "DOUBTFUL", "SI": "YES", "SÍ": "YES", "NO": "NO",
        "alta": "high", "media": "medium", "baja": "low"}
DRUG = {"fluconazol": "fluconazole", "voriconazol": "voriconazole", "itraconazol": "itraconazole",
        "posaconazol": "posaconazole", "isavuconazol": "isavuconazole", "ketoconazol": "ketoconazole",
        "miconazol": "miconazole", "clotrimazol": "clotrimazole", "anfotericina b": "amphotericin B",
        "caspofungina": "caspofungin", "micafungina": "micafungin", "anidulafungina": "anidulafungin",
        "5-flucitosina": "5-flucytosine", "flucitosina": "5-flucytosine", "nistatina": "nystatin",
        "terbinafina": "terbinafine"}
COUNTRY = {"Estados Unidos": "USA", "EE. UU.": "USA", "Brasil": "Brazil", "España": "Spain", "Turquía": "Turkey",
           "Japón": "Japan", "Francia": "France", "Australia": "Australia", "India": "India", "Israel": "Israel",
           "Colombia": "Colombia"}
STOP = {"hospital", "university", "universidad", "center", "centre", "medical", "college", "institute"}
S_COLS = ["No.", "ID", "Title", "Year", "Journal", "DOI", "PDF file", "Decision", "Main reason", "Meta-analysis",
          "IC1", "IC2", "IC3", "IC4", "IC5", "IC6", "IC7", "IC8", "Exclusions", "Compartments", "Source", "Country",
          "Study type", "Identification", "Susceptibility method", "Standard/version", "Antifungals",
          "N C. tropicalis isolates", "Molecular", "Programme/institution", "Period", "Evidence", "Notes",
          "Automatic flags", "Mentions of tropicalis"]
E_KEYS = ["decision_final", "motivo_cambio", "diseno", "pais", "region_ciudad", "entorno", "multicentrico", "n_centros",
          "periodo_inicio", "periodo_fin", "compartimentos", "fuentes_detalle", "poblacion", "infeccion_tipo",
          "n_tropicalis_total", "n_candida_total", "metodo_identificacion", "metodo_sensibilidad", "norma_documento",
          "norma_version", "tipo_punto_corte", "exposicion_azoles", "fungicidas_agricolas_probados", "ic8",
          "apto_metaanalisis", "confianza", "observaciones"]
R_KEYS = ["compartimento", "fuente", "periodo", "antifungico", "metodo", "norma", "n_probados", "n_S", "n_SDD_I", "n_R",
          "n_NWT", "cmi_rango", "cmi50", "cmi90", "cmi_mg", "unidad", "nota"]
M_KEYS = ["compartimento", "gen", "alteracion", "tipo", "n_examinados", "n_con_alteracion",
          "n_resistentes_con_alteracion", "n_sensibles_con_alteracion", "metodo", "nota"]
G_KEYS = ["compartimento", "metodo", "n_tipificados", "tipo", "n_aislados", "n_resistentes_azoles", "clado_reportado", "nota"]
D_KEYS = ["compartimento", "antifungico", "periodo", "n_probados", "n_R", "descripcion"]

LABEL_FIX = {"B023": "Yashavanth"}


def newest(p):
    f = sorted(glob.glob(p))
    assert f, p
    return f[-1]

def lst(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[;,/]", v) if x.strip()]
    return list(v) if isinstance(v, list) else [v]

def norm(s):
    return " ".join(sorted(set(re.findall(r"[a-záéíóúñ]{4,}", (s if isinstance(s, str) else "").lower())) - STOP))[:80]

class Tr:
    """English version of every value: codes and drugs by table, free text from the translation file."""
    def __init__(self, path):
        self.map = json.load(open(path, encoding="utf-8"))
        self.missing = []
    def __call__(self, rid, field, v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        if isinstance(v, list):
            return "; ".join(str(self(rid, field, x)) for x in v)
        s = str(v).strip()
        if s == "":
            return None
        if s.upper() in CODE:
            return CODE[s.upper()]
        if s in CODE:
            return CODE[s]
        if s.lower() in DRUG:
            return DRUG[s.lower()]
        if s in COUNTRY:
            return COUNTRY[s]
        if re.fullmatch(r"(C[1-6](; ?C[1-6])*|mixto|EC\d+)", s):
            return s.replace("mixto", "mixed")
        if re.fullmatch(r"[\d.,\-–<>=≤≥ /]+|µg/mL|mg/L", s):
            return s
        key = f"{rid}|{field}|{s}"
        if key in self.map:
            return self.map[key]
        if s in self.map:
            return self.map[s]
        self.missing.append(key)
        return s

def main(f_scr, f_ext, f_tr):
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S")
    reg = pd.read_csv(newest(f"{REG}/reference_check_candidates_v1_*.csv")).set_index("report_id")
    scr = json.load(open(f_scr, encoding="utf-8"))
    ext = {r["id"]: r for r in json.load(open(f_ext, encoding="utf-8"))}
    tr = Tr(f_tr)
    md_dir = os.path.join(os.path.dirname(os.path.dirname(f_scr)), "md")
    rows = []
    for r in scr:
        rid = r["id"]; g = reg.loc[rid]
        md = glob.glob(os.path.join(md_dir, rid + "_*.md"))
        mentions = len(re.findall("tropicalis", open(md[0], encoding="utf-8").read(), re.I)) if md else None
        rows.append([9000 + int(rid[1:]), rid, g.title, int(g.year) if pd.notna(g.year) else None, g.journal, g.doi,
                     g.pdf_file, tr(rid, "decision", r.get("decision")), tr(rid, "motivo_principal", r.get("motivo_principal")),
                     tr(rid, "metaanalisis", r.get("metaanalisis"))] +
                    [tr(rid, f"IC{i}", r.get(f"IC{i}")) for i in range(1, 9)] +
                    ["; ".join(lst(r.get("EC"))) or None, "; ".join(lst(r.get("compartimentos"))) or None,
                     tr(rid, "fuente", r.get("fuente")), "; ".join(COUNTRY.get(p, p) for p in lst(r.get("pais"))) or None,
                     tr(rid, "tipo_estudio", r.get("tipo_estudio")), tr(rid, "metodo_identificacion", r.get("metodo_identificacion")),
                     tr(rid, "metodo_sensibilidad", r.get("metodo_sensibilidad")), tr(rid, "norma_version", r.get("norma_version")),
                     "; ".join(DRUG.get(str(a).lower(), a) for a in lst(r.get("antifungicos"))) or None,
                     r.get("n_aislados_tropicalis"), tr(rid, "molecular", r.get("molecular")),
                     tr(rid, "programa_institucion", r.get("programa_institucion")), r.get("periodo") or None,
                     tr(rid, "evidencia", r.get("evidencia")), tr(rid, "notas", r.get("notas")), None, mentions])
    all_ = pd.DataFrame(rows, columns=S_COLS)
    # EC12 groups: B reports included at screening, against the included reports of the deposited workbook
    old = pd.read_excel(FT, sheet_name="All")
    old_g = pd.read_excel(FT, sheet_name="Possible duplicates EC12")
    inc_old = old[old.Decision == "INCLUDE"]
    key_old = collections.defaultdict(list)
    for _, o in inc_old.iterrows():
        k = norm(o["Programme/institution"])
        if k:
            key_old[(str(o.Country), k)].append(o)
    group_of = {(str(r.Country), r["Programme/institution (normalised)"]): int(r.Group) for _, r in old_g.iterrows()}
    nxt = int(old_g.Group.max()) + 1
    ec = []
    for _, b in all_[all_.Decision == "INCLUDE"].iterrows():
        k = (str(b.Country), norm(b["Programme/institution"]))
        if not k[1] or not key_old.get(k):
            continue
        grp = group_of.get(k)
        if grp is None:
            grp = nxt; nxt += 1; group_of[k] = grp
            for o in key_old[k]:
                ec.append([grp, k[0], k[1], o["No."], o.Title, o.Year, o.Period, o["N C. tropicalis isolates"], o["Programme/institution"]])
        ec.append([grp, k[0], k[1], b["No."], b.Title, b.Year, b.Period, b["N C. tropicalis isolates"], b["Programme/institution"]])
    ec12 = pd.DataFrame(ec, columns=list(old_g.columns))
    # extraction workbook
    X = pd.ExcelFile("08_phase6_data_extraction/data_extraction_tropicalis.xlsx")
    cols = {s: list(X.parse(s, nrows=0).columns) for s in ("Studies", "Resistance", "Molecular", "Genotype", "Dynamics", "Clade 4")}
    st, rs, mo, ge, dy, c4 = [], [], [], [], [], []
    for rid, r in sorted(ext.items()):
        g = reg.loc[rid]; e = r.get("estudio") or {}
        # surname = the author string without the trailing initials, so "da Silva CM" gives "da Silva"; PubMed inverts the
        # name of B023 ("R Y" for Yashavanth R.), corrected by hand in LABEL_FIX (2026-10-28)
        surname = LABEL_FIX.get(rid, re.sub(r"\s+[A-Z]{1,3}$", "", str(g.first_author).strip()))
        label = f"{surname} {int(g.year)}" if pd.notna(g.year) else surname
        bib = [9000 + int(rid[1:]), rid, label]
        country = "; ".join(COUNTRY.get(p, p) for p in lst(e.get("pais")))
        evals = []
        for k in E_KEYS:
            v = e.get(k)
            if k == "pais":
                evals.append(country or None)
            elif k == "compartimentos":
                evals.append("; ".join(lst(v)) or None)
            else:
                evals.append(tr(rid, k, v))
        st.append(bib + [g.title, int(g.year) if pd.notna(g.year) else None, g.journal, g.doi] + evals +
                  [len(r.get("resistencia") or []), len(r.get("molecular") or []), len(r.get("genotipo") or []),
                   tr(rid, "clado4", (r.get("clado4") or {}).get("menciona")), g.pdf_file])
        ctx = bib + [country or None, e.get("periodo_inicio"), e.get("periodo_fin"), tr(rid, "decision_final", e.get("decision_final")),
                     tr(rid, "apto_metaanalisis", e.get("apto_metaanalisis"))]
        for key, keys, out in (("resistencia", R_KEYS, rs), ("molecular", M_KEYS, mo), ("genotipo", G_KEYS, ge), ("dinamica", D_KEYS, dy)):
            for x in r.get(key) or []:
                out.append(ctx + [tr(rid, f"{key}.{c}", x.get(c)) for c in keys])
        c = r.get("clado4") or {}
        if str(c.get("menciona", "")).upper() in ("SI", "SÍ"):
            c4.append(bib + [g.title, country, c.get("n_aislados_clado4"), c.get("n_resistentes_azoles_clado4"),
                             "; ".join(lst(c.get("compartimentos_clado4"))), "; ".join(map(str, lst(c.get("dst_st")))),
                             tr(rid, "clado4.evidencia", c.get("evidencia")), tr(rid, "clado4.nota", c.get("nota"))])
    if tr.missing:
        miss = os.path.join(os.path.dirname(f_tr), f"untranslated_values_{stamp}.txt")
        open(miss, "w", encoding="utf-8").write("\n".join(sorted(set(tr.missing))) + "\n")
        sys.exit(f"{len(set(tr.missing))} values without translation, listed in {miss}; nothing was written.")
    os.makedirs(REG, exist_ok=True); os.makedirs(EXT, exist_ok=True)
    p_scr = f"{REG}/full_text_screening_r3_v1_{stamp}.xlsx"
    with pd.ExcelWriter(p_scr) as w:
        all_.to_excel(w, sheet_name="All", index=False)
        ec12.to_excel(w, sheet_name="Possible duplicates EC12", index=False)
    p_ext = f"{EXT}/data_extraction_r3_v1_{stamp}.xlsx"
    with pd.ExcelWriter(p_ext) as w:
        for name, data in (("Studies", st), ("Resistance", rs), ("Molecular", mo), ("Genotype", ge), ("Dynamics", dy), ("Clade 4", c4)):
            pd.DataFrame(data, columns=cols[name]).to_excel(w, sheet_name=name, index=False)
    print(run_log.write(__file__, [f_scr, f_ext, f_tr, newest(f"{REG}/reference_check_candidates_v1_*.csv"), FT],
                        [p_scr, p_ext], screened=len(all_), extracted=len(ext), resistance_rows=len(rs), ec12_rows=len(ec12)))
    print(p_scr, p_ext, sep="\n")

if __name__ == "__main__":
    main(*sys.argv[1:4])
