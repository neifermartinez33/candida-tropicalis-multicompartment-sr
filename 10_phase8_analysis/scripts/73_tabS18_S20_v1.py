#!/usr/bin/env python3
"""73_tabS18_S20_v1.py (2026-11-02)

Tables S18 (SX4 to SX9), S19 (SX10, SX11 and the laboratory coding) and S20 (estimates by WHO region), from the results of
72_posthoc_sensitivity_v1.R, and version 8 of the deviation log (Table S12), which adds the analyses as row 29.

Usage, from the project root:
  python3 10_phase8_analysis/scripts/73_tabS18_S20_v1.py
Outputs: 12_documents/supplementary/tables/tabS18_*, tabS19_*, tabS20_* and tabS12_deviation_log_v8_* (xlsx and CSV).
"""
import glob
from datetime import datetime

import openpyxl
import pandas as pd
from openpyxl.styles import Alignment, Font

RES = "10_phase8_analysis/results/"
OUT = "12_documents/supplementary/tables/"
STAMP = datetime.now().strftime("%Y-%m-%dT%H%M%S")
last = lambda p: sorted(f for f in glob.glob(p) if "PROVISIONAL" not in f)[-1]  # noqa: E731
STATUS = {"pooled": "Pooled", "not_pooled_tau2_AR18b": "Not pooled: upper limit of τ² above 25", "below_minimum_AR12": "Not pooled: below the minimum condition",
          "not_pooled_boundary_AR18a": "Not pooled: all collections at the boundary"}
LEVEL = {"method of the ECV": "Method of the ECV", "reference broth microdilution": "Reference broth microdilution", "commercial_microdilution_SYO": "Sensititre YeastOne",
         "commercial_ATB_FUNGUS": "ATB FUNGUS", "gradient_diffusion": "Gradient diffusion", "commercial_automated_VITEK2": "VITEK 2"}
REGION = {"AFR": "African Region", "AMR": "Region of the Americas", "EMR": "Eastern Mediterranean Region", "EUR": "European Region", "SEAR": "South-East Asia Region", "WPR": "Western Pacific Region"}
ANALYSIS = {"SX4": "SX4, without case reports and case series", "SX5": "SX5, without laboratory evaluations", "SX6": "SX6, without collections of fewer than five isolates",
            "SX7": "SX7, SX4 to SX6 together", "SX8": "SX8, without the largest collection"}


def fmt(r):
    return dict(k=r.k, events_isolates=f"{r.events:,}/{r.isolates:,}", status=STATUS[r.status], population_mean_pct="" if pd.isna(r.p_marginal) else f"{100 * r.p_marginal:.1f}",
                ci95=("" if pd.isna(r.marg_lower) else f"{100 * r.marg_lower:.1f}–{100 * r.marg_upper:.1f}"), median_pct="" if pd.isna(r.p_median) else f"{100 * r.p_median:.1f}",
                tau2_upper_limit="" if pd.isna(r.tau2_upper) else f"{r.tau2_upper:.1f}")


def split(s):
    c, a, o, g = s.split(" | ")
    return dict(compartment=c, agent=a, outcome=o, criterion=g)


def write(name, sheets):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    p = f"{OUT}{name}_{STAMP}"
    for title, caption, df in sheets:
        ws = wb.create_sheet(title)
        ws.append([caption])
        ws["A1"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, df.shape[1]))
        ws.row_dimensions[1].height = 48
        ws.append(list(df.columns))
        for c in ws[2]:
            c.font = Font(bold=True)
        for row in df.itertuples(index=False):
            ws.append(list(row))
        for i, col in enumerate(df.columns, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = min(46, max(11, int(df[col].astype(str).str.len().max() or 10) + 2))
    wb.save(p + ".xlsx")
    sheets[0][2].to_csv(p + ".csv", index=False)
    print(p)


def main():
    d = pd.read_csv(last(RES + "ma_posthoc_v1_*.csv"), keep_default_na=True)
    lr = pd.read_csv(last(RES + "ma_posthoc_lrt_v1_*.csv"))
    base = pd.read_csv(last(RES + "ma_results_v3_*[0-9].csv"))
    base["stratum"] = base.compartment + " | " + base.agent + " | " + base.outcome + " | " + base.regime_stratum
    bm = base.set_index("stratum").p_marginal
    a = pd.DataFrame([{**split(r.stratum), "analysis": ANALYSIS[r.analysis], "main_mean_pct": f"{100 * bm[r.stratum]:.1f}", **fmt(r)} for r in d[d.analysis.isin(ANALYSIS)].itertuples()])
    b = pd.DataFrame([{**split(r.stratum), "method": LEVEL[r.level], "main_mean_pct": "" if pd.isna(bm.get(r.stratum)) else f"{100 * bm[r.stratum]:.1f}", **fmt(r)} for r in d[d.analysis == "SX9"].itertuples()])
    write("tabS18_posthoc_human_host_v1", [("SX9 test method", "Table S18. Human host: ECV-based outcomes with the method for which each ECV was established and by test method, and resistance with reference broth microdilution only (SX9). Not prespecified. Reference broth microdilution: CLSI or unspecified for CLSI ECVs and breakpoints, EUCAST for EUCAST ones.", b),
                                           ("SX4 to SX8", "Table S18, continued. Pooled strata of the human host refitted without case reports and case series, laboratory evaluations, small collections and the largest collection (SX4 to SX8). Not prespecified.", a)])
    c = pd.DataFrame([{**split(r.stratum), "main_status": STATUS.get(base.set_index("stratum").status[r.stratum], "Not pooled: upper limit of τ² above 25"), "main_mean_pct": "" if pd.isna(bm[r.stratum]) else f"{100 * bm[r.stratum]:.1f}", **fmt(r)} for r in d[d.analysis == "SX10"].itertuples()])
    s = d[d.analysis == "SX11"]
    e = pd.DataFrame([{**split(st), "collections_left_out": len(g), "fits_still_pooled": int((g.status == "pooled").sum()), "lowest_mean_pct": f"{100 * g.p_marginal.min():.1f}" if g.p_marginal.notna().any() else "", "highest_mean_pct": f"{100 * g.p_marginal.max():.1f}" if g.p_marginal.notna().any() else ""} for st, g in s.groupby("stratum")])
    lab = pd.read_csv("10_phase8_analysis/data/lookups/lab_coding_v1.csv")
    write("tabS19_posthoc_nonhuman_v1", [("SX10", "Table S19. Non-human strata that met the minimum condition, refitted with one collection per laboratory, the one with most isolates tested (SX10). Not prespecified. Laboratories: reports linked by at least two shared authors (Crossref); three reports without authors retrieved (Alves 2015, Caldas 2017, Spanamberg 2009) were kept as independent.", c),
                                         ("SX11", "Table S19, continued. Pooled non-human strata leaving out one collection at a time (SX11). Not prespecified.", e), ("Laboratory coding", "Table S19, continued. Laboratory assigned to each non-human report.", lab)])
    f = pd.DataFrame([{"agent": split(r.stratum)["agent"], "criterion": split(r.stratum)["criterion"], "who_region": REGION[r.level], **fmt(r)} for r in d[d.analysis == "REG"].itertuples()])
    g = pd.DataFrame([dict(agent=r.agent, multinational_collections="included" if r.with_multinational else "excluded", k=r.k, chi_square=f"{r.chisq:.1f}", df=r.df, p="<0.001" if r.p < 0.001 else f"{r.p:.3f}", tau2_without_region=f"{r.tau2_null:.2f}", tau2_with_region=f"{r.tau2_region:.2f}", variance_reduction_pct=f"{100 * r.reduction:.0f}") for r in lr.itertuples()])
    write("tabS20_posthoc_who_region_v1", [("By region", "Table S20. Human host: fluconazole and voriconazole resistance with current breakpoints by WHO region. Exploratory, not prespecified. Multinational collections are not assigned to a region.", f), ("Likelihood-ratio tests", "Table S20, continued. Likelihood-ratio tests of WHO region.", g)])
    wb = openpyxl.load_workbook(last(OUT + "tabS12_deviation_log_v7_*.xlsx"))
    ws = wb.active
    row = [ws.max_row, "Analyses added after the results had been seen: ECV outcomes with the method of each ECV and by test method and resistance with reference broth microdilution only (SX9); non-human strata with one collection per laboratory (SX10) and leaving out one collection (SX11); human-host exclusions (SX4 to SX8); fluconazole and voriconazole resistance by WHO region (Tables S18 to S20).",
           "Collections of one laboratory may share isolates and most ECVs were established for broth microdilution. Pooled non-human estimates remain in Table 4 and Table S16 as the registered analysis but are no longer reported as findings.", ws.cell(ws.max_row, 4).value, ws.cell(ws.max_row, 5).value]
    print("S12 columns", [c.value for c in ws[2]][:5], [c.value for c in ws[ws.max_row]][3:5], [c.value for c in ws[1]][:5])
    ws.append(row)
    p = f"{OUT}tabS12_deviation_log_v8_{STAMP}"
    wb.save(p + ".xlsx")
    pd.DataFrame(ws.values).to_csv(p + ".csv", index=False, header=False)
    print(p)
    print(g.to_string())


if __name__ == "__main__":
    main()
