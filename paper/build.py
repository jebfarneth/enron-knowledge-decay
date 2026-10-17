"""Build the paper: figures and every reported number come from the results files.

Reads the main pipeline's results (results/, data/processed/) and the
labelled checks (data/labels/, kept outside git), draws the figures, fills
paper.html.tmpl and prints it to PDF with headless Chrome. A number that is
not in a results file (a published figure from another paper, a parameter
from config.yaml) is a named constant below.

Usage: .venv/bin/python paper/build.py
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from string import Template

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
BUILD = PAPER / "build"
FROZEN = Path.home() / "projects/enron_frozen_run_2026-09-26"  # the run before the time-shifted copy correction
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PDF_NAME = "Farneth_Can_Email_Reveal_Who_Outranks_Whom.pdf"

PUBLISHED_DEGREE = "83.88%"  # Agarwal et al. (2012), degree on their 13,724 pairs
PUBLISHED_CC_CHECK = "69.7%"  # Agarwal et al. (2014), Cc check on their graph
# From the time-shifted copy correction (README, "Phase 3: time-shifted copies"), computed against the
# frozen run's near-duplicate scan; not written to a results file.
CAUGHT_LONG, CAUGHT_NEAR, MAX48_EXTRA = 1538, 64, 7
QUOTED_NEAR_HALFWAY = 5  # long-shift pairs whose quoted send time is within an hour of halfway (label rationales)
UNIT_TESTS, CORPUS_CHECKS = 255, 17  # `make all` on the corrected run, 2026-10-13

SURFACE = "#ffffff"
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, GREEN, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
YELLOW = "#eda100"  # categorical slot 4; blue, orange, aqua (GREEN) and yellow pass the palette validator together
COLLECTION = ROOT / "collection" / "results"  # the custodian-selection experiment (collection/PLAN*.md)
OWNER_WEAKEST = "43%"  # dean-c: share of its messages with its inferred owner on them (collection/corrections.py log)
CLABELS = {"degree": "Degree", "pagerank": "PageRank", "anchored_degree": "Anchored degree",
           "anchored_strength": "Anchored strength", "talked_about": "Talked about"}
CCOLOR = {"degree": BLUE, "talked_about": ORANGE, "pagerank": GREEN, "anchored_degree": YELLOW}
RC = {
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.size": 8.5, "axes.titlesize": 9, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelcolor": MUTED, "axes.edgecolor": GRID,
    "axes.spines.top": False, "axes.spines.right": False, "xtick.color": MUTED, "ytick.color": TEXT,
    "text.color": TEXT, "svg.fonttype": "path",
}

LABELS = {
    "degree": "Degree (distinct contacts)",
    "pagerank": "PageRank",
    "in_strength": "Email received (weighted)",
    "out_strength": "Email sent (messages)",
    "betweenness": "Betweenness (exact)",
    "mention_degree": "Mention-network degree",
    "mentioned_to": "People mentioned to them",
    "third_party_mentioned_to": "Others mentioned to them",
    "custodian": "Mailbox collected (custodian)",
}
MENTION = {"mention_degree", "mentioned_to", "third_party_mentioned_to"}
PTYPES = {"all": "all", "core": "core", "inter": "inter", "non-core": "noncore"}
VARIANTS = {
    "main": "Main population",
    "matched, no path through any uncertain record (strict)": "No uncertain records (strict)",
    "matched, including uncertain records": "Uncertain records included",
    "matched, mixed-position endpoints excluded only (earlier main)": "Earlier main population",
    "name+address matches only": "Name and address matches only",
    "positions closed before mapping": "Positions closed before mapping",
    "cycle arcs removed before closure": "Cycle arcs removed before closure",
    "without Lay and Skilling": "Without Lay and Skilling",
    "macro average over dominant employees": "Each manager weighted equally",
    "all pairs, unmatched employees scored 0": "All pairs, unmatched scored 0",
}


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def num(x: float) -> str:
    return f"{x * 100:.1f}"


def signed(x: float) -> str:
    v = round(x * 100, 1)
    return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.1f}"


def ci(low: float, high: float) -> str:
    return f"{num(low)}–{num(high)}"


def comma(n: int) -> str:
    return f"{int(n):,}"


def load() -> dict:
    r, p, lab = ROOT / "results", ROOT / "data/processed", ROOT / "data/labels"
    return {
        "gold": pd.read_csv(r / "baselines_gold_standard.csv"),
        "gold_paired": pd.read_csv(r / "gold_standard_paired.csv"),
        "gold_sens": pd.read_csv(r / "gold_standard_sensitivity.csv"),
        "title": pd.read_csv(r / "baselines_formal_rank.csv"),
        "title_paired": pd.read_csv(r / "baselines_paired_differences.csv"),
        "title_sens": pd.read_csv(r / "baselines_sensitivity.csv"),
        "coverage": json.loads((r / "gold_standard_coverage.json").read_text()),
        "mentions": json.loads((r / "mention_resolution.json").read_text()),
        "cleaning": json.loads((r / "cleaning_crosscheck.json").read_text()),
        "funnel": json.loads((p / "funnel.json").read_text())["funnel"],
        "person_text": json.loads((p / "person_text.json").read_text()),
        "links": json.loads((p / "links.json").read_text()),
        "shift": json.loads((lab / "shifted_copies/scores.json").read_text()),
        "shift_human": json.loads((lab / "shifted_copies/human_scores.json").read_text()),
        "pilot": json.loads((lab / "phase3_pilot/scores.json").read_text()),
    }


def numbers(d: dict) -> dict[str, str]:
    n: dict[str, str] = {"published_degree": PUBLISHED_DEGREE, "published_cc_check": PUBLISHED_CC_CHECK}
    gold = d["gold"]
    for row in gold.itertuples():
        key = f"{row.measure}_{PTYPES[row.pairs_type]}"
        n[f"g_{key}"] = pct(row.accuracy)
        n[f"gci_{key}"] = ci(row.ci_low, row.ci_high)
        n[f"gpairs_{PTYPES[row.pairs_type]}"] = comma(row.pairs)
    for row in d["gold_paired"].itertuples():
        key = f"{row.measure}_{PTYPES[row.pairs_type]}"
        n[f"d_{key}"] = signed(row.difference)
        n[f"dci_{key}"] = f"{signed(row.ci_low)} to {signed(row.ci_high)}"
    for row in d["title"].itertuples():
        n[f"t_{row.measure}"] = pct(row.accuracy)
        n[f"tci_{row.measure}"] = ci(row.ci_low, row.ci_high)
        n["tpairs"], n["tpeople"] = comma(row.pairs), comma(row.people)
    for row in d["title_paired"].itertuples():
        key = f"{row.measure}_{row.versus}"
        n[f"td_{key}"] = signed(row.difference)
        n[f"tdci_{key}"] = f"{signed(row.ci_low)} to {signed(row.ci_high)}"
    ts = d["title_sens"].set_index(["variant", "measure"])["accuracy"]
    n["t_degree_no_ceo"] = pct(ts[("CEO and President removed", "degree")])
    n["t_degree_people_only"] = pct(ts[("people-only graph", "degree")])
    n["t_degree_max10"] = pct(ts[("messages with at most 10 recipients", "degree")])

    sens = d["gold_sens"]
    sall = sens[sens.pairs_type == "all"].set_index(["variant", "measure"])
    pairs = sens[sens.pairs_type == "all"].groupby("variant")["pairs"].first()
    n["raw_degree"] = pct(sall.loc[("all pairs, raw-address degree over windowed, deduplicated mail, max over release "
                                    "addresses", "raw_address_degree"), "accuracy"])
    n["macro_degree"] = pct(sall.loc[("macro average over dominant employees", "degree"), "accuracy"])
    n["macro_pagerank"] = pct(sall.loc[("macro average over dominant employees", "pagerank"), "accuracy"])
    n["macro_mentioned_to"] = pct(sall.loc[("macro average over dominant employees", "mentioned_to"), "accuracy"])
    n["no_ls_degree"] = pct(sall.loc[("without Lay and Skilling", "degree"), "accuracy"])
    n["strict_degree"] = pct(sall.loc[("matched, no path through any uncertain record (strict)", "degree"), "accuracy"])
    n["strict_pairs"] = comma(pairs["matched, no path through any uncertain record (strict)"])
    main_pairs = int(gold[(gold.measure == "degree") & (gold.pairs_type == "all")]["pairs"].iloc[0])
    ls_pairs = main_pairs - int(pairs["without Lay and Skilling"])
    n["ls_pairs"], n["ls_share"] = comma(ls_pairs), pct(ls_pairs / main_pairs)
    inter = int(gold[(gold.measure == "degree") & (gold.pairs_type == "inter")]["pairs"].iloc[0])
    n["inter_share"] = pct(inter / main_pairs, 0)
    noncore = int(gold[(gold.measure == "degree") & (gold.pairs_type == "non-core")]["pairs"].iloc[0])
    n["noncore_share"] = pct(noncore / main_pairs, 0)
    deg = sall.xs("degree", level="measure")["accuracy"]
    deg = pd.concat([deg, pd.Series({"main": gold[(gold.measure == "degree") & (gold.pairs_type == "all")]
                                     ["accuracy"].iloc[0]})])
    n["degree_min"], n["degree_max"] = pct(deg.min()), pct(deg.max())
    n["degree_span"] = num(deg.max() - deg.min())
    allp = gold[gold.pairs_type == "all"].set_index("measure")["accuracy"]
    gp = d["gold_paired"]
    noncore_gaps = gp[(gp.pairs_type == "non-core")
                      & gp.measure.isin(["pagerank", "mentioned_to", "third_party_mentioned_to"])]["difference"]
    n["nc_gap_min"], n["nc_gap_max"] = num(noncore_gaps.min()), num(noncore_gaps.max())
    inter_acc = gold[(gold.pairs_type == "inter") & gold.measure.isin(LABELS) & (gold.measure != "out_strength")]
    n["inter_lo"], n["inter_hi"] = pct(inter_acc["accuracy"].min()), pct(inter_acc["accuracy"].max())
    n["best_network"] = pct(allp[["degree", "pagerank", "in_strength", "out_strength", "betweenness"]].max())
    leading = gp[(gp.pairs_type == "all") & gp.measure.isin(["pagerank", "mention_degree", "mentioned_to",
                                                             "third_party_mentioned_to"])]["difference"]
    n["lead_gap"] = num(leading.abs().max())
    gaps = []
    for variant in VARIANTS:
        if variant == "main":
            continue
        gaps.append(sall.loc[(variant, "mentioned_to"), "accuracy"] - sall.loc[(variant, "degree"), "accuracy"])
    n["sens_gap_min"], n["sens_gap_max"] = num(min(gaps)), num(max(gaps))
    n["sens_variants"] = str(len(gaps))

    cov = d["coverage"]
    n.update({
        "gold_employees": comma(cov["employees"]), "gold_with_email": comma(cov["employees_with_email"]),
        "gold_pairs": comma(cov["pairs"]["main"]), "paper_pairs": comma(cov["paper"]["pairs"]),
        "paper_relations": comma(cov["paper"]["immediate_relations"]),
        "full_core": comma(cov["main_pairs_by_type"]["core"]), "full_inter": comma(cov["main_pairs_by_type"]["inter"]),
        "full_noncore": comma(cov["main_pairs_by_type"]["non-core"]),
        "paper_core": comma(cov["paper"]["core"]), "paper_inter": comma(cov["paper"]["inter"]),
        "paper_noncore": comma(cov["paper"]["non_core"]),
        "mixed_records": str(cov["employees_with_mixed_positions"]),
        "multi_records": str(cov["employees_with_several_people_and_positions"]),
        "uncertain_records": str(cov["employees_uncertain"]),
        "main_pairs": comma(cov["main_population_pairs"]),
        "positions_first_pairs": comma(cov["pairs"]["positions closed before mapping"]),
        "cycle_pairs": comma(cov["pairs"]["cycle arcs removed before closure"]),
    })
    for status, count in cov["match_status"].items():
        n["match_" + status.replace("+", "_").replace(" ", "_")] = comma(count)

    m = d["mentions"]
    n.update({
        "m_tagged": comma(m["messages_tagged"]), "m_with": comma(m["messages_with_mentions"]),
        "m_links": comma(m["resolved_links"]), "m_main": comma(m["resolved_links_main"]),
        "m_self": comma(m["excluded_self"]), "m_office": comma(m["excluded_office"]),
        "m_company": comma(m["excluded_company"]), "m_abbrev": comma(m["excluded_abbreviation"]),
        "m_not_person": comma(m["excluded_not_person_text"]), "m_people": comma(m["people_with_mention_links"]),
        "cc_checks": comma(m["cc_checks"]), "cc_acc": pct(m["cc_check_accuracy"]),
        "cc_single": pct(m["cc_check_single_accuracy"]), "cc_ambiguous": pct(m["cc_check_ambiguous_accuracy"]),
    })

    c = d["cleaning"]
    n.update({
        "clean_n": comma(c["messages"]), "clean_agree": pct(c["whitespace_normalized_agreement"]),
        "clean_empty_ours": pct(c["empty_output"]["ours"]), "clean_empty_erp": pct(c["empty_output"]["email_reply_parser"]),
        "clean_hdr_ours": pct(c["residue"]["quoted_header"]["ours"]),
        "clean_hdr_erp": pct(c["residue"]["quoted_header"]["email_reply_parser"]),
        "clean_fwd_ours": pct(c["residue"]["forwarded_by"]["ours"], 2),
        "clean_fwd_erp": pct(c["residue"]["forwarded_by"]["email_reply_parser"]),
    })

    f = d["funnel"]
    for key in ("parsed_files", "in_window", "dropped_outside_window", "dropped_duplicate_content", "unique_messages",
                "candidate_separate_sends", "with_authored_text", "automated_messages", "structured_records",
                "signature_only_messages", "routine_messages_excluded_from_text", "probable_time_shifted_copies",
                "analysis_messages", "analysis_senders", "with_quoted_material"):
        n[f"f_{key}"] = comma(f[key])
    pt = d["person_text"]
    n["f_person_text"], n["f_people"] = comma(pt["person_text_messages"]), comma(pt["person_text_people"])
    lk = d["links"]
    n.update({"links": comma(lk["links"]), "reply_links": comma(lk["reply_links"]),
              "forward_links": comma(lk["forward_links"])})

    s = d["shift"]
    lab, chk = s["labels"], s["checks"]
    for frame in ("long", "near", "control"):
        om = lab[frame]["one_message"]
        n[f"sh_{frame}_pairs"] = comma(chk[frame]["pairs"])
        n[f"sh_{frame}_n"], n[f"sh_{frame}_k"] = str(om["n"]), str(om["k"])
        n[f"sh_{frame}_ci"] = f"{num(om['low'])}–{num(om['high'])}%"
        n[f"sh_{frame}_both"] = comma(chk[frame]["pairs_with_one_export_folder_holding_both"])
        n[f"sh_{frame}_notes"] = comma(chk[frame]["pairs_earlier_only_in_notes_later_only_in_outlook"])
    clock = chk["long"]["pairs_by_gap_and_clock"]
    n["sh_10_daylight"], n["sh_10_total"] = comma(clock["10"]["daylight"]), comma(sum(clock["10"].values()))
    n["sh_11_standard"], n["sh_11_total"] = comma(clock["11"]["standard"]), comma(sum(clock["11"].values()))
    n["sh_12_standard"], n["sh_12_total"] = comma(clock["12"]["standard"]), comma(sum(clock["12"].values()))
    near = chk["near"]["pairs_by_gap_and_clock"]
    n["sh_near_5"] = comma(sum(near["5"].values()))
    ch = chk["chance"]
    n["sh_chance_whole"] = f"{ch['expected_two_send_pairs_on_whole_hours']:.2f}"
    n["sh_chance_near"] = f"{ch['expected_two_send_pairs_near_whole_hours']:.2f}"
    n["sh_observed"] = comma(ch["observed_long_and_near_pairs"])
    n["sh_labelled_shifted"] = str(lab["long"]["one_message"]["n"] + lab["near"]["one_message"]["n"])
    human = d["shift_human"]
    n["hu_items"] = str(human["items"])
    n["hu_shifted"] = str(human["shifted_items"])
    n["hu_shifted_one"] = str(human["shifted_person_verdicts"].get("one_message", 0))
    n["hu_controls"] = str(human["control_items"])
    n["hu_controls_two"] = str(human["control_person_verdicts"].get("two_sends", 0))
    n["hu_agree"] = str(human["agree_with_ai"])
    long_between = lab["long"]["time_supported"].get("neither", 0)
    near_dated = lab["near"]["time_supported"].get("earlier", 0) + lab["near"]["time_supported"].get("later", 0)
    n["q_long"], n["q_near"], n["q_dated"] = str(long_between), str(near_dated), str(long_between + near_dated)
    n["q_halfway"] = str(QUOTED_NEAR_HALFWAY)
    n["caught_long"], n["caught_near"], n["max48_extra"] = comma(CAUGHT_LONG), comma(CAUGHT_NEAR), str(MAX48_EXTRA)
    n["unit_tests"], n["corpus_checks"] = str(UNIT_TESTS), str(CORPUS_CHECKS)

    pilot = d["pilot"]["adjudicated"]
    rep, men = pilot["replies"], pilot["mentions"]
    for level in ("high", "medium", "low"):
        pc = rep[f"reply_{level}"]["parent_correct"]
        n[f"p_{level}"], n[f"p_{level}_n"] = pct(pc["rate"]), str(pc["n"])
        n[f"p_{level}_ci"] = ci(pc["low"], pc["high"])
    n["p_precision"] = pct(rep["weighted"]["precision"], 0)
    n["p_recall"] = pct(rep["weighted"]["recall_within_frame"], 0)
    mm = men["main"]["resolved_correctly"]
    n["p_mention"], n["p_mention_n"], n["p_mention_ci"] = pct(mm["rate"]), str(mm["n"]), ci(mm["low"], mm["high"])
    n["p_mention_outside"] = str(men["main"]["referent"]["outside_person"])
    n["p_mention_wrong"] = str(mm["n"] - mm["k"])
    n["p_office_outside"] = str(men["excluded_office"]["referent"]["outside_person"])
    n["p_office_n"] = str(men["excluded_office"]["resolved_correctly"]["n"])
    return n


def correction_deltas() -> dict[str, str]:
    """Largest change in any accuracy between the frozen run and the corrected run."""
    if not FROZEN.exists():
        raise SystemExit(f"{FROZEN} (the run before the correction) is needed for the before/after numbers")
    before = json.loads((FROZEN / "processed/funnel.json").read_text())["funnel"]
    after = json.loads((ROOT / "data/processed/funnel.json").read_text())["funnel"]
    out = {"old_flagged": comma(before["probable_time_shifted_copies"]),
           "analysis_removed": comma(before["analysis_messages"] - after["analysis_messages"])}
    main, anyt = 0.0, 0.0
    for name in ("baselines_gold_standard.csv", "baselines_formal_rank.csv"):
        old, new = pd.read_csv(FROZEN / "results" / name), pd.read_csv(ROOT / "results" / name)
        delta = (new["accuracy"] - old["accuracy"]).abs()
        anyt = max(anyt, delta.max())
        main = max(main, delta[new["pairs_type"] == "all"].max() if "pairs_type" in new else delta.max())
    return out | {"delta_main": f"{main * 100:.2f}", "delta_any": f"{anyt * 100:.1f}"}


def measure_color(measure: str) -> str:
    return ORANGE if measure in MENTION else GREY if measure == "custodian" else BLUE


def finish_axis(ax, lo: float, hi: float, xlabel: str | None = None) -> None:
    ax.set_xlim(lo, hi)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    if xlabel:
        ax.set_xlabel(xlabel)


def fig_funnel(d: dict, path: Path) -> None:
    """Single-column figure (about 3.3 in wide in the two-column layout)."""
    f, pt = d["funnel"], d["person_text"]
    steps = [("Files in the corpus", f["parsed_files"]), ("Dated 1998–2002", f["in_window"]),
             ("Duplicate copies removed", f["unique_messages"]),
             ("With authored text", f["with_authored_text"]),
             ("Analysis set", f["analysis_messages"]),
             ("Sender is a person", pt["person_text_messages"])]
    with plt.rc_context(RC | {"font.size": 7.5}):
        fig, ax = plt.subplots(figsize=(3.4, 2.1))
        labels, values = zip(*steps[::-1])
        ax.barh(range(len(values)), values, color=BLUE, height=0.62)
        for i, v in enumerate(values):
            ax.text(v + 8000, i, f"{v / 1000:,.0f}k ({v / f['parsed_files']:.0%})", va="center", fontsize=6.8)
        ax.set_yticks(range(len(values)), labels)
        finish_axis(ax, 0, 700000, "Messages")
        ax.set_xticks([0, 200000, 400000, 600000])
        ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}k")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def fig_main(d: dict, path: Path) -> None:
    gold = d["gold"][d["gold"].pairs_type == "all"].set_index("measure")
    title = d["title"].set_index("measure")
    order = [m for m in gold.sort_values("accuracy").index if m in LABELS]
    with plt.rc_context(RC):
        fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.1), sharey=True, gridspec_kw={"wspace": 0.08})
        for ax, table, name in ((axes[0], title, f"Title proxy ({comma(title['pairs'].iloc[0])} pairs)"),
                                (axes[1], gold, f"Gold standard ({comma(gold.loc['degree', 'pairs'])} pairs)")):
            rows = pd.DataFrame([{"measure": m, **table.loc[m, ["accuracy", "ci_low", "ci_high"]].to_dict()}
                                 if m in table.index else {"measure": m, "accuracy": float("nan"), "ci_low": float("nan"),
                                                           "ci_high": float("nan")} for m in order])
            ax.axvline(0.5, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
            for i, row in rows.iterrows():
                if pd.isna(row.accuracy):
                    ax.text(0.52, i, "not available", va="center", fontsize=7, color=MUTED)
                    continue
                color = measure_color(row.measure)
                ax.hlines(i, row.ci_low, row.ci_high, color=color, linewidth=1.8)
                ax.plot(row.accuracy, i, "o", color=color, markersize=5.5, markeredgecolor=SURFACE,
                        markeredgewidth=1.2)
                ax.text(row.ci_high + 0.008, i, pct(row.accuracy), va="center", fontsize=7)
            finish_axis(ax, 0.4, 1.04, "Pairs ordered correctly (95% interval)")
            ax.set_title(name)
        axes[0].set_yticks(range(len(order)), [LABELS[m] for m in order])
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def fig_pair_types(d: dict, path: Path) -> None:
    gold = d["gold"]
    measures = ["custodian", "mentioned_to", "pagerank", "degree"]
    types = [("non-core", "Neither mailbox collected"), ("inter", "One mailbox collected"),
             ("core", "Both mailboxes collected")]
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(6.3, 3.0))
        ticks, ticklabels = [], []
        y = 0.0
        for ptype, label in types:
            block = gold[gold.pairs_type == ptype].set_index("measure")
            for k, m in enumerate(measures):
                row = block.loc[m]
                color = GREEN if m == "pagerank" else measure_color(m)
                yy = y + k * 0.62
                if row.ci_low != row.ci_high:
                    ax.hlines(yy, row.ci_low, row.ci_high, color=color, linewidth=1.8)
                ax.plot(row.accuracy, yy, "o", color=color, markersize=5.5, markeredgecolor=SURFACE,
                        markeredgewidth=1.2, label=LABELS[m] if ptype == "non-core" else None)
                ax.text(max(row.ci_high, row.accuracy) + 0.008, yy, pct(row.accuracy), va="center", fontsize=7)
            ticks.append(y + 0.93)
            ticklabels.append(f"{label}\n({comma(block.loc['degree', 'pairs'])} pairs)")
            y += 3.4
        ax.axvline(0.5, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
        ax.set_yticks(ticks, ticklabels)
        finish_axis(ax, 0.4, 1.04, "Pairs ordered correctly (95% interval)")
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles[::-1], labels[::-1], loc="lower left", fontsize=7, frameon=False, bbox_to_anchor=(0.0, 1.0),
                  ncol=4, handletextpad=0.2, columnspacing=1.0)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def fig_sensitivity(d: dict, path: Path) -> None:
    sens = d["gold_sens"]
    sall = sens[sens.pairs_type == "all"]
    gold = d["gold"][d["gold"].pairs_type == "all"]
    rows = []
    for variant, label in VARIANTS.items():
        src = gold if variant == "main" else sall[sall.variant == variant]
        acc = src.set_index("measure")["accuracy"]
        rows.append({"label": f"{label} ({comma(src['pairs'].iloc[0])})", **{m: acc[m] for m in
                     ("degree", "pagerank", "mentioned_to", "custodian")}})
    table = pd.DataFrame(rows).sort_values("degree").reset_index(drop=True)
    with plt.rc_context(RC):
        fig, ax = plt.subplots(figsize=(6.3, 3.2))
        for m, marker in (("custodian", "o"), ("degree", "o"), ("pagerank", "D"), ("mentioned_to", "s")):
            color = GREEN if m == "pagerank" else measure_color(m)
            ax.plot(table[m], table.index, marker, color=color, markersize=6, markeredgecolor=SURFACE,
                    markeredgewidth=0.8, label=LABELS[m], linestyle="none")
        for i, row in table.iterrows():
            lo, hi = min(row.degree, row.pagerank, row.mentioned_to), max(row.degree, row.pagerank, row.mentioned_to)
            ax.hlines(i, lo, hi, color=GRID, linewidth=3, zorder=0)
        main = table.index[table.label.str.startswith("Main population")][0]
        ax.axhspan(main - 0.45, main + 0.45, color="#f2f1ec", zorder=-1)
        ax.set_yticks(table.index, table.label)
        finish_axis(ax, 0.45, 1.0, "Pairs ordered correctly")
        ax.legend(loc="lower left", fontsize=7, frameon=False, bbox_to_anchor=(0.0, 1.0), ncol=4,
                  handletextpad=0.2, columnspacing=1.0)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def fig_shift(d: dict, path: Path) -> None:
    chk = d["shift"]["checks"]
    with plt.rc_context(RC):
        fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.3), gridspec_kw={"width_ratios": [1.5, 1], "wspace": 0.3})
        for ax, frame, gaps, title in ((axes[0], "long", list(range(9, 18)), "A whole 9 to 17 hours apart"),
                                       (axes[1], "near", [1, 3, 5, 6, 7, 24], "Within a minute of whole hours")):
            clock = chk[frame]["pairs_by_gap_and_clock"]
            day = [clock.get(str(g), {}).get("daylight", 0) for g in gaps]
            std = [clock.get(str(g), {}).get("standard", 0) for g in gaps]
            x = range(len(gaps))
            ax.bar(x, day, color=ORANGE, width=0.7, label="Sent in daylight time")
            ax.bar(x, std, bottom=day, color=BLUE, width=0.7, label="Sent in standard time")
            for i, (a, b) in enumerate(zip(day, std)):
                if a + b:
                    ax.text(i, a + b, comma(a + b), ha="center", va="bottom", fontsize=7)
            ax.set_xticks(list(x), [str(g) for g in gaps])
            ax.set_xlabel("Gap between the two timestamps (hours)")
            ax.set_title(f"{title} ({comma(chk[frame]['pairs'])} pairs)")
            ax.grid(axis="y", color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            ax.set_ylim(0, max(a + b for a, b in zip(day, std)) * 1.15)
        axes[0].set_ylabel("Pairs")
        axes[0].legend(fontsize=7, frameon=False, loc="upper right")
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def collection_data() -> dict:
    return {"summary": json.loads((COLLECTION / "summary.json").read_text()),
            "corr": json.loads((COLLECTION / "corrections_summary.json").read_text()),
            "runs": pd.read_csv(COLLECTION / "corrections.csv"),
            "resolution": json.loads((COLLECTION / "resolution_summary.json").read_text()),
            "confident": json.loads((COLLECTION / "confident_names.json").read_text()),
            "confident_rows": pd.read_csv(COLLECTION / "confident_names.csv")}


def robustness_numbers(c: dict, base: dict[str, str]) -> dict[str, str]:
    """Part 3 (names resolved inside each collection) and Part 4 (high-confidence names), collection/PLAN_resolution.md."""
    r, h, rows = c["resolution"], c["confident"], c["confident_rows"]
    rx = r["expectations"]
    size = lambda k, m: r["by_size"][str(k)][m]  # noqa: E731
    talk25, talk10 = size(25, "talked_about")["in_collection"], size(10, "talked_about")["in_collection"]
    diff = lambda subset, pairs: rows[(rows["subset"] == subset) & (rows["measure"] == "mentioned_to")  # noqa: E731
                                      & (rows["pairs_type"] == pairs)].iloc[0]
    pilot = h["pilot_precision"]
    n = {**{k: base[k] for k in ("col_deg25_width", "col_deg10_lo", "col_deg10_hi")},
        "res_collections": comma(r["collections"]),
        "res_large_draws": str(r["random_draws"]["50"]),
        "res_talk25_lo": pct(talk25["range_95"][0]), "res_talk25_hi": pct(talk25["range_95"][1]),
        "res_talk25_width": f"{rx['R1_range_at_25_points']['talked_about_in_collection']:.1f}",
        "res_talk25_median": pct(talk25["median"]),
        "res_talk10_lo": pct(talk10["range_95"][0]), "res_talk10_hi": pct(talk10["range_95"][1]),
        "res_talk25_change": signed(size(25, "talked_about")["median_paired_change"]),
        "res_bias10_talked": signed(size(10, "talked_about")["bias"]["median"]),
        "res_bias25_talked": signed(size(25, "talked_about")["bias"]["median"]),
        "res_links25_more": pct(r["by_size"]["25"]["links_kept_share"]["median"] - 1, 0),
        "res_talk10_full_lo": pct(size(10, "talked_about")["full_corpus_resolution"]["range_95"][0]),
        "res_talk10_full_hi": pct(size(10, "talked_about")["full_corpus_resolution"]["range_95"][1]),
        "res_top20_25_talked": pct(size(25, "talked_about")["top20"]["median"], 0),
        "res_r1": "met" if rx["R1_met"] else "not met", "res_r2": "met" if rx["R2_met"] else "not met",
        "hc_full_share": pct(h["link_share_by_kind"]["full name"], 0),
        "hc_pilot_full_k": str(pilot["full names"]["correct"]), "hc_pilot_full_n": str(pilot["full names"]["n"]),
        "hc_pilot_word_k": str(pilot["one word"]["correct"]), "hc_pilot_word_n": str(pilot["one word"]["n"]),
        "hc_pilot_word_outside": str(pilot["one word"]["outside_person"]),
        "hc_pilot_outside": str(pilot["all"]["outside_person"]),
    }
    for key, subset in (("full", "full names"), ("one", "one candidate"), ("all", "all links")):
        for pairs, tag in (("non-core", "nc"), ("all", "all")):
            d = diff(subset, pairs)
            n[f"hc_{tag}_{key}"] = signed(d["difference_vs_degree"])
            n[f"hc_{tag}_{key}_ci"] = f"{signed(d['ci_low'])} to {signed(d['ci_high'])}"
    n["hc_talk_full"] = pct(h["accuracy"]["full names"]["talked_about"]["all"])
    n["hc_talk_all"] = pct(h["accuracy"]["all links"]["talked_about"]["all"])
    # Section 6.6 says every outside-person error was a one-word name; the pilot labels must bear that out.
    if pilot["full names"]["outside_person"] or pilot["one word"]["outside_person"] != pilot["all"]["outside_person"]:
        raise SystemExit("pilot: outside-person errors are not all one-word names; revise the Section 6.6 wording")
    # Wording that depends on Part 3. The plan (collection/PLAN_resolution.md, "What changes in the paper") fixes it:
    # with R1 and R2 met, talked about's stability is reported under in-collection resolution.
    if not (rx["R1_met"] and rx["R2_met"]):
        raise SystemExit("R1 or R2 not met: write the softened wording the plan requires before building")
    w = n["res_talk25_width"]
    n["abs_talk"] = (f"A count of the people who talk about someone in messages that person is not on is far more stable "
                     f"(a {w}-point range, with names resolved inside each collection) at a cost of {{cost}} points on the full corpus.")
    n["intro_talk"] = f"varies far less with the collection (a {w}-point range at 25 mailboxes, with names resolved inside each collection)"
    n["impl_talk"] = f"a count of who is talked about, rather than who emails whom, moves over {w} points."
    n["lim_resolution"] = ("Names were resolved again inside each collection (Section 7.3), but addresses are still matched to "
                           "people with the full corpus's identity table, which every measure uses, degree included;")
    n["res_paragraph"] = (
        f"<p>These figures resolve names with the whole corpus. An analyst holding 25 mailboxes would know only the people "
        f"in those mailboxes' network, so after a review of an earlier draft we resolved every name again inside each of "
        f"{n['res_collections']} collections, with only that collection's people and network distances (all random draws at "
        f"10 and 25 mailboxes, {n['res_large_draws']} at each larger size, the ordered collections and the full corpus; "
        f"planned in advance in "
        f"<code>collection/PLAN_resolution.md</code>). Fewer candidates leave fewer ties, so slightly more names resolve "
        f"(a median {n['res_links25_more']} more links at 25 mailboxes). Talked about remains the most stable measure: at 25 "
        f"mailboxes its accuracy ranges from {n['res_talk25_lo']} to {n['res_talk25_hi']} ({w} points, against "
        f"{n['col_deg25_width']} for degree; median change {n['res_talk25_change']} points), and its collection bias stays "
        f"closer to zero than degree's at every size ({n['res_bias10_talked']} at 10 mailboxes, {n['res_bias25_talked']} at "
        f"25). Both expectations stated for this check, R1 and R2 in Table 3, were met. At 10 mailboxes the range widens, to {n['res_talk10_lo']} to "
        f"{n['res_talk10_hi']} (from {n['res_talk10_full_lo']} to {n['res_talk10_full_hi']} with full-corpus resolution), "
        f"still about half of degree's {n['col_deg10_lo']} to {n['col_deg10_hi']}.</p>")
    return n


def points(x: float) -> str:
    """A change in percentile rank (a fraction of the ranking), in percentile points with a sign."""
    return signed(x)


def collection_numbers(c: dict, lead_gap: str) -> dict[str, str]:
    s, f, runs = c["summary"], c["corr"], c["runs"]
    e, fx = s["expectations"], f["expectations"]
    size = lambda k: s["by_size"][str(k)]  # noqa: E731
    corr = lambda k, m, x: f["by_size"][str(k)][m][x]  # noqa: E731
    full = runs[runs["policy"] == "full"].iloc[0]  # unrounded, unlike the summary files
    deg25 = size(25)["degree|all"]["range_95"]
    talk25, talk10 = corr(25, "talked_about", "accuracy")["range_95"], corr(10, "talked_about", "accuracy")["range_95"]
    width = e["E1_range_of_degree_accuracy_at_25_points"]
    n = {
        "col_collections": comma(len(runs)), "col_draws": str(int((runs["policy"] == "random").sum() / 6)),
        "col_mailboxes": "150", "col_sizes": "10, 25, 50, 75, 100 and 125",
        "col_deg25_lo": pct(deg25[0]), "col_deg25_hi": pct(deg25[1]),
        "col_deg25_median": pct(size(25)["degree|all"]["median"]), "col_deg25_width": f"{width:.1f}",
        "col_ratio": f"{width / float(lead_gap):.1f}",
        "col_deg10_lo": pct(size(10)["degree|all"]["range_95"][0]), "col_deg10_hi": pct(size(10)["degree|all"]["range_95"][1]),
        "col_bias_share10": pct(e["E2_share_of_draws_with_positive_bias"]["10"]),
        "col_bias_share25": pct(e["E2_share_of_draws_with_positive_bias"]["25"]),
        "col_pr_bias10": points(size(10)["collection_bias"]["median"]),
        "col_top20_25": pct(size(25)["top20_overlap"]["median"], 0), "col_top20_50": pct(size(50)["top20_overlap"]["median"], 0),
        "col_top20_100": pct(size(100)["top20_overlap"]["median"], 0),
        "col_spear10": f"{size(10)['spearman_pagerank']['median']:.2f}",
        "col_spear125": f"{size(125)['spearman_pagerank']['median']:.2f}",
        "col_senior10": pct(size(10)["senior first"]["degree|all"]), "col_random10": pct(size(10)["degree|all"]["median"]),
        "col_busiest10": pct(size(10)["busiest first"]["degree|all"]),
        "col_senior100": pct(size(100)["senior first"]["degree|all"], 2),
        "col_random100": pct(size(100)["degree|all"]["median"], 2),
        "col_senior_sizes": str(sum(fx_ for fx_ in e["E3_senior_first_above_random_median"].values())),
        "cor_full_degree": pct(full["degree|all"]), "cor_full_talked": pct(full["talked_about|all"]),
        "cor_full_anchored": pct(full["anchored_degree|all"]),
        "cor_full_strength": pct(full["anchored_strength|all"]),
        "cor_talk_cost": num(full["degree|all"] - full["talked_about|all"]),
        "cor_talk25_lo": pct(talk25[0]), "cor_talk25_hi": pct(talk25[1]), "cor_talk25_width": num(talk25[1] - talk25[0]),
        "cor_talk10_lo": pct(talk10[0]), "cor_talk10_hi": pct(talk10[1]),
        "cor_anch25_width": f"{fx['F3_range_at_25_points']['anchored_degree']:.1f}",
        "cor_bias10_degree": points(corr(10, "degree", "bias")["median"]),
        "cor_bias10_anchored": points(corr(10, "anchored_degree", "bias")["median"]),
        "cor_bias10_talked": points(corr(10, "talked_about", "bias")["median"]),
        "cor_bias25_talked": points(corr(25, "talked_about", "bias")["median"]),
        "cor_bias25_degree": points(corr(25, "degree", "bias")["median"]),
        "cor_top20_25_talked": pct(corr(25, "talked_about", "top20")["median"], 0),
        "cor_top20_25_anchored": pct(corr(25, "anchored_degree", "top20")["median"], 0),
        "cor_top20_25_degree": pct(corr(25, "degree", "top20")["median"], 0),
        "cor_top20_25_pagerank": pct(corr(25, "pagerank", "top20")["median"], 0),
        "owner_weakest": OWNER_WEAKEST,
    }
    met = lambda flag: "Met" if flag else "Not met"  # noqa: E731
    rows = [
        ("E1", "At 25 mailboxes, degree's accuracy range over random collections is wider than the largest gap between "
               f"leading measures ({lead_gap} points)", f"{n['col_deg25_width']} points", met(e["E1_met"])),
        ("E2", "Collected employees rank higher than in the full corpus in at least 95% of random draws, at every size",
         f"{n['col_bias_share10']} at 10 mailboxes, at least {n['col_bias_share25']} from 25 up", met(e["E2_met"])),
        ("E3", "Senior-first collections beat the median random collection on degree at every size",
         f"{n['col_senior_sizes']} of 6 sizes", met(e["E3_met"])),
        ("F1", "Anchored degree's collection bias is closer to zero than degree's at every size",
         f"Overcorrects at 10 ({n['cor_bias10_anchored']} against {n['cor_bias10_degree']}); closer from 25 up", met(fx["F1_met"])),
        ("F2", "Talked about's collection bias is closer to zero than degree's at every size",
         f"{n['cor_bias10_talked']} against {n['cor_bias10_degree']} at 10; closer at every size", met(fx["F2_met"])),
        ("F3", "At 25 mailboxes, anchored degree's accuracy range is narrower than degree's",
         f"{n['cor_anch25_width']} against {n['col_deg25_width']} points", met(fx["F3_met"])),
    ]
    n["table_collection"] = "\n".join(
        f"<tr><td>{a}</td><td>{b}</td><td>{c_}</td><td>{d_}</td></tr>" for a, b, c_, d_ in rows)
    return n


def fig_collection(c: dict, path: Path) -> None:
    runs = c["runs"]
    random, full = runs[runs["policy"] == "random"], runs[runs["policy"] == "full"].iloc[0]
    sizes = sorted(random["mailboxes"].unique()) + [150]

    def band(column: str):
        g = random.groupby("mailboxes")[column]
        lo, mid, hi = (list(g.quantile(q)) + [full[column]] for q in (0.025, 0.5, 0.975))
        return lo, mid, hi

    with plt.rc_context(RC):
        fig, axes = plt.subplots(1, 2, figsize=(6.8, 3.0), gridspec_kw={"wspace": 0.3})
        for ax, metric, measures, title, scale in (
                (axes[0], "{}|all", ["degree", "anchored_degree", "talked_about"], "(a) Accuracy on the main pairs", 1),
                (axes[1], "bias|{}", ["degree", "pagerank", "anchored_degree", "talked_about"],
                 "(b) Collected employees' rank shift", 100)):
            if scale == 100:
                ax.axhline(0, color=MUTED, linewidth=0.8)
            for m in measures:
                lo, mid, hi = band(metric.format(m))
                ax.fill_between(sizes, [scale * v for v in lo], [scale * v for v in hi], color=CCOLOR[m], alpha=0.14,
                                linewidth=0)
                ax.plot(sizes, [scale * v for v in mid], color=CCOLOR[m], linewidth=2, marker="o", markersize=4,
                        markeredgecolor=SURFACE, markeredgewidth=1, label=CLABELS[m])
            ax.set_xticks(sizes, [str(k) for k in sizes], fontsize=7)
            ax.set_xlim(0, 158)
            ax.set_xlabel("Mailboxes collected (of 150)")
            ax.grid(axis="y", color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            ax.set_title(title)
        axes[0].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        axes[0].set_ylim(0.5, 0.95)
        axes[1].set_ylabel("Percentile points")
        handles, labels = axes[1].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.04), fontsize=7.5)
        fig.savefig(path, bbox_inches="tight")
        plt.close(fig)


def tables(d: dict, n: dict) -> dict[str, str]:
    gold, title = d["gold"], d["title"].set_index("measure")
    order = ["pagerank", "degree", "in_strength", "betweenness", "out_strength",
             "third_party_mentioned_to", "mentioned_to", "mention_degree", "custodian"]
    body = []
    for m in order:
        g = gold[gold.measure == m].set_index("pairs_type")
        t = "—"
        if m in title.index:
            t = f"{pct(title.loc[m, 'accuracy'])} <span class=ci>({ci(title.loc[m, 'ci_low'], title.loc[m, 'ci_high'])})</span>"
        interval = ci(g.loc["all", "ci_low"], g.loc["all", "ci_high"])
        cells = [LABELS[m], t, f"{pct(g.loc['all', 'accuracy'])} <span class=ci>({interval})</span>"]
        cells += [pct(g.loc[p, "accuracy"]) for p in ("core", "inter", "non-core")]
        cls = " class=group" if m in ("third_party_mentioned_to", "custodian") else ""
        body.append(f"<tr{cls}>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    results = "\n".join(body)

    paired = d["gold_paired"].set_index(["measure", "pairs_type"])
    rows = []
    for m in ("pagerank", "mention_degree", "mentioned_to", "third_party_mentioned_to", "custodian"):
        cells = [LABELS[m]]
        for p in ("all", "inter", "non-core"):
            r = paired.loc[(m, p)]
            cells.append(f"{signed(r.difference)} <span class=ci>({signed(r.ci_low)} to {signed(r.ci_high)})</span>")
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return {"table_results": results, "table_paired": "\n".join(rows)}


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "figures").mkdir(exist_ok=True)
    d = load()
    n = numbers(d) | correction_deltas()
    fig_funnel(d, BUILD / "figures/funnel.svg")
    fig_main(d, BUILD / "figures/main.svg")
    fig_pair_types(d, BUILD / "figures/pair_types.svg")
    fig_sensitivity(d, BUILD / "figures/sensitivity.svg")
    fig_shift(d, BUILD / "figures/shift.svg")
    c = collection_data()
    n |= collection_numbers(c, n["lead_gap"])
    n |= robustness_numbers(c, n)
    n["abs_talk"] = n["abs_talk"].replace("{cost}", n["cor_talk_cost"])
    rx = c["resolution"]["expectations"]
    r_rows = [
        ("R1", "With names resolved inside each collection, talked about's accuracy range at 25 mailboxes is narrower "
               "than degree's", f"{n['res_talk25_width']} against {n['col_deg25_width']} points", "Met" if rx["R1_met"] else "Not met"),
        ("R2", "With names resolved inside each collection, talked about's collection bias is closer to zero than "
               "degree's at every size", f"{n['res_bias10_talked']} at 10; closer at every size",
         "Met" if rx["R2_met"] else "Not met"),
    ]
    n["table_collection"] += "\n" + "\n".join(
        f"<tr><td>{a}</td><td>{b_}</td><td>{c_}</td><td>{d_}</td></tr>" for a, b_, c_, d_ in r_rows)
    fig_collection(c, BUILD / "figures/collection.svg")
    n |= tables(d, n)
    html = Template((PAPER / "paper.html.tmpl").read_text()).substitute(n)
    (BUILD / "paper.html").write_text(html)
    (BUILD / "numbers.json").write_text(json.dumps({k: v for k, v in n.items() if not k.startswith("table_")},
                                                   indent=1, ensure_ascii=False))
    pdf = PAPER / PDF_NAME
    pdf.unlink(missing_ok=True)
    # Headless Chrome on macOS can exit non-zero over display warnings after writing the file, so the
    # check is that the PDF was written, not the exit code.
    with tempfile.TemporaryDirectory() as profile:
        run = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                              f"--user-data-dir={profile}", f"--print-to-pdf={pdf}", "--virtual-time-budget=5000",
                              (BUILD / "paper.html").as_uri()], capture_output=True, text=True)
    if not pdf.exists() or "bytes written" not in run.stderr + run.stdout:
        raise SystemExit(f"Chrome did not write the PDF:\n{run.stderr[-2000:]}")
    print(f"Wrote {pdf}")


if __name__ == "__main__":
    main()
