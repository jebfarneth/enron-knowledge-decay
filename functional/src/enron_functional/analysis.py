"""The pre-registered analysis (PLAN.md, "Analysis"; decisions 4 and 10 to 14).

Main sample: absences starting 2000-01-01 to 2001-11-30 that do not include
December 24 to January 1, of people who sent at least 20 person-text
messages in the 56 days before, with their control windows.

  away effect   answered-within-24h share in absence windows minus control
                windows (messages pooled), 95% interval from the person bootstrap
  H1            logistic regression of answered on away, the five signals and the
                three baselines (standardized over absences) and their away
                interactions; the five away x signal coefficients with bootstrap
                intervals and Holm-adjusted p; person-disjoint 5-fold log loss of
                baselines alone against baselines plus signals; the same model with
                formal rank on the people matched to the title list
  H2            away x names_backup, with the baselines and their interactions
  H3            each person's away effect, shrunk (empirical Bayes), with formal rank
  placebo       the 2-week control window as "away" against the other three
  secondary     stalled, rerouted, catch_up: absence minus the mean of its control
                windows, averaged over absences, with the person bootstrap
  sensitivity   the away effect and H1 under each run listed in the plan

Writes results/analysis.json and results/analysis_people.csv (H3; names,
counts and estimates, no message text).

Usage: uv run python -m enron_functional.analysis
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationWarning

from .config import load_config

SIGNALS = ["betweenness", "constraint", "topic_ownership", "pointed_to", "named_backup"]
BASELINES = ["sent", "received", "degree"]
LOGGED = {"betweenness", "pointed_to", "named_backup", "sent", "received", "degree"}
DRAWS = 1000
SEED = 20261013
FOLDS = 5


def select(windows: pd.DataFrame, run: str) -> pd.DataFrame:
    """Windows of the absences a run uses."""
    away = windows[windows["window"] == "away"]
    base = away["main_period"] & ~away["holiday_week"]
    keep = {
        "main": base & (away["baseline_sent"] >= 20),
        "auto_replies": base & (away["baseline_sent"] >= 20) & away["auto_only"],
        "threshold_10": base & (away["baseline_sent"] >= 10),
        "post_filing": ~away["main_period"] & ~away["holiday_week"] & (away["baseline_sent"] >= 20),
        "year_end": away["main_period"] & away["holiday_week"] & (away["baseline_sent"] >= 20),
    }[run]
    return windows[windows["absence_id"].isin(away.loc[keep, "absence_id"])]


def standardized(signals: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """One row per absence: log(1 + x) for counts, then z-scores over the absences given."""
    out = signals[["absence_id"]].copy()
    for c in columns:
        x = np.log1p(signals[c]) if c in LOGGED else signals[c].astype(float)
        sd = x.std(ddof=0)
        out["z_" + c] = (x - x.mean()) / sd if sd > 0 else 0.0
    return out


def design(frame: pd.DataFrame, moderators: list[str]) -> tuple[np.ndarray, list[str]]:
    away = frame["away"].to_numpy(float)
    columns, names = [np.ones(len(frame)), away], ["const", "away"]
    for m in moderators:
        z = frame["z_" + m].to_numpy(float)
        columns += [z, away * z]
        names += [m, "away:" + m]
    return np.column_stack(columns), names


PROGRESS = {"fits": 0, "file": None}


def fit(y: np.ndarray, x: np.ndarray) -> np.ndarray | None:
    PROGRESS["fits"] += 1
    if PROGRESS["file"] is not None and PROGRESS["fits"] % 50 == 0:
        PROGRESS["file"].write_text(f"{PROGRESS['fits']}\n")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        warnings.simplefilter("error", PerfectSeparationWarning)
        warnings.simplefilter("ignore", ConvergenceWarning)
        try:
            result = sm.Logit(y, x).fit(disp=0, maxiter=100)
        except Exception:
            return None
    return None if not result.mle_retvals.get("converged", True) else result.params


def person_draws(frame: pd.DataFrame, rng: np.random.Generator) -> list[np.ndarray]:
    """Row indices of each bootstrap draw: people resampled with replacement."""
    people = frame["person"].unique()
    rows = {p: np.flatnonzero(frame["person"].to_numpy() == p) for p in people}
    return [np.concatenate([rows[p] for p in rng.choice(people, size=len(people), replace=True)])
            for _ in range(DRAWS)]


def bootstrap_p(draws: np.ndarray) -> float:
    return float(min(1.0, 2 * min((draws <= 0).mean(), (draws >= 0).mean())))


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    order = sorted(pvalues, key=pvalues.get)
    adjusted, running = {}, 0.0
    for rank, name in enumerate(order):
        running = max(running, min(1.0, (len(order) - rank) * pvalues[name]))
        adjusted[name] = running
    return adjusted


def logistic(frame: pd.DataFrame, moderators: list[str], outcome: str, tests: list[str],
             draws: list[np.ndarray]) -> dict:
    """Point estimates of every coefficient, and bootstrap intervals and p for `tests` (interaction names)."""
    x, names = design(frame, moderators)
    y = frame[outcome].to_numpy(float)
    point = fit(y, x)
    if point is None:
        return {"error": "the model did not converge"}
    index = [names.index(t) for t in tests]
    boot = [b[index] for b in (fit(y[d], x[d]) for d in draws) if b is not None]
    boot = np.array(boot)
    out = {"messages": int(len(frame)), "people": int(frame["person"].nunique()),
           "absences": int(frame["absence_id"].nunique()), "draws_converged": int(len(boot)),
           "coefficients": {n: round(float(v), 4) for n, v in zip(names, point)}, "tests": {}}
    pvalues = {}
    for j, t in enumerate(tests):
        pvalues[t] = bootstrap_p(boot[:, j]) if len(boot) else float("nan")
        out["tests"][t] = {"estimate": round(float(point[names.index(t)]), 4),
                           "interval_95": [round(float(np.percentile(boot[:, j], 2.5)), 4),
                                           round(float(np.percentile(boot[:, j], 97.5)), 4)] if len(boot) else None,
                           "p": round(pvalues[t], 4)}
    if len(tests) > 1:
        for t, p in holm(pvalues).items():
            out["tests"][t]["p_holm"] = round(p, 4)
    return out


def away_effect(frame: pd.DataFrame, outcome: str, draws: list[np.ndarray]) -> dict:
    away = frame["away"].to_numpy(bool)
    y = frame[outcome].to_numpy(float)

    def diff(rows: np.ndarray) -> float:
        a, yy = away[rows], y[rows]
        return yy[a].mean() - yy[~a].mean() if a.any() and (~a).any() else float("nan")

    point = diff(np.arange(len(frame)))
    boot = np.array([diff(d) for d in draws])
    boot = boot[~np.isnan(boot)]
    return {"answered_away": round(float(y[away].mean()), 4), "answered_control": round(float(y[~away].mean()), 4),
            "messages_away": int(away.sum()), "messages_control": int((~away).sum()),
            "difference": round(float(point), 4),
            "interval_95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
            "p": round(bootstrap_p(boot), 4)}


def cross_validated(frame: pd.DataFrame, outcome: str) -> dict:
    """Out-of-fold log loss of baselines alone and of baselines plus signals, folds of whole people."""
    rng = np.random.default_rng(SEED)
    people = frame["person"].unique()
    fold_of = dict(zip(rng.permutation(people), np.arange(len(people)) % FOLDS))
    folds = frame["person"].map(fold_of).to_numpy()
    y = frame[outcome].to_numpy(float)
    losses = {}
    for name, moderators in {"baselines": BASELINES, "baselines_and_signals": BASELINES + SIGNALS}.items():
        x, _ = design(frame, moderators)
        total = 0.0
        for k in range(FOLDS):
            train, test = folds != k, folds == k
            params = fit(y[train], x[train])
            if params is None:
                return {"error": f"a fold of {name} did not converge"}
            p = np.clip(1 / (1 + np.exp(-x[test] @ params)), 1e-9, 1 - 1e-9)
            total += -(y[test] * np.log(p) + (1 - y[test]) * np.log(1 - p)).sum()
        losses[name] = round(total / len(y), 5)
    losses["difference"] = round(losses["baselines_and_signals"] - losses["baselines"], 5)
    return losses


def people_effects(frame: pd.DataFrame, rank: pd.DataFrame, persons: set[str]) -> pd.DataFrame:
    """H3: each person's away effect, raw and shrunk toward the mean."""
    g = frame.groupby(["person", "away"])["answered"].agg(["sum", "count"]).unstack("away")
    g = g.dropna()
    g = g[(g[("count", True)] >= 10) & (g[("count", False)] >= 10)]
    g = g[g.index.isin(persons)]
    p1, n1 = g[("sum", True)] / g[("count", True)], g[("count", True)]
    p0, n0 = g[("sum", False)] / g[("count", False)], g[("count", False)]
    d = p1 - p0
    v = p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0
    mean = d.mean()
    tau2 = max(0.0, d.var(ddof=1) - v.mean()) if len(d) > 1 else 0.0
    shrunk = mean + (tau2 / (tau2 + v.replace(0, v[v > 0].min() if (v > 0).any() else 1e-6))) * (d - mean)
    out = pd.DataFrame({"person": g.index, "messages_away": n1.astype(int).values, "messages_control": n0.astype(int).values,
                        "answered_away": p1.round(4).values, "answered_control": p0.round(4).values,
                        "away_effect": d.round(4).values, "away_effect_shrunk": shrunk.round(4).values})
    out = out.merge(rank, on="person", how="left")
    return out.sort_values("away_effect_shrunk").reset_index(drop=True)


def secondary(windows_out: pd.DataFrame, rng: np.random.Generator) -> dict:
    result = {}
    for outcome in ("stalled", "rerouted", "catch_up"):
        w = windows_out.dropna(subset=[outcome])
        away = w[w["window"] == "away"].set_index("absence_id")[[outcome, "person"]]
        control = w[w["window"] != "away"].groupby("absence_id")[outcome].mean()
        both = away.join(control.rename("control"), how="inner")
        both["diff"] = both[outcome] - both["control"]
        people = both["person"].unique()
        by_person = {p: both.loc[both["person"] == p, "diff"].to_numpy() for p in people}
        boot = [np.concatenate([by_person[p] for p in rng.choice(people, len(people))]).mean() for _ in range(DRAWS)]
        result[outcome] = {"absences": int(len(both)), "people": int(len(people)),
                           "away": round(float(both[outcome].mean()), 4), "control": round(float(both["control"].mean()), 4),
                           "difference": round(float(both["diff"].mean()), 4),
                           "interval_95": [round(float(np.percentile(boot, 2.5)), 4), round(float(np.percentile(boot, 97.5)), 4)],
                           "p": round(bootstrap_p(np.array(boot)), 4)}
    return result


def assemble(windows, messages, signals, run: str, days: int = 56) -> pd.DataFrame:
    chosen = select(windows, run)
    sig = signals[(signals["days"] == days) & signals["absence_id"].isin(chosen["absence_id"])]
    z = standardized(sig, SIGNALS + BASELINES)
    frame = messages[messages["absence_id"].isin(sig["absence_id"])].merge(z, on="absence_id", how="inner")
    frame = frame.merge(windows[["absence_id", "names_backup"]].drop_duplicates("absence_id"), on="absence_id")
    frame["away"] = frame["window"] == "away"
    # absences need messages in both their absence and at least one control window
    has = frame.groupby("absence_id")["away"].agg(["any", "all"])
    keep = has.index[has["any"] & ~has["all"]]
    return frame[frame["absence_id"].isin(keep)].reset_index(drop=True)


def main() -> None:
    config = load_config()
    data, source, results = config["paths"]["data"], config["paths"]["source"], config["paths"]["results"]
    windows = pd.read_parquet(data / "windows.parquet")
    messages = pd.read_parquet(data / "outcome_messages.parquet")
    signals = pd.read_parquet(data / "signals.parquet")
    rank = pd.read_parquet(source / "formal_rank.parquet", columns=["person_key", "title", "level"])
    rank = rank.dropna(subset=["person_key"]).drop_duplicates("person_key").rename(columns={"person_key": "person"})
    persons = set(pd.read_parquet(source / "person_types.parquet").query("entity_type == 'person'")["person_key"])
    rng = np.random.default_rng(SEED)
    PROGRESS["file"] = data / "analysis_progress.txt"        # logistic fits done, for watching a long run
    tests = ["away:" + s for s in SIGNALS]
    report = {}

    frame = assemble(windows, messages, signals, "main")
    draws = person_draws(frame, rng)
    report["sample"] = {"absences": int(frame["absence_id"].nunique()), "people": int(frame["person"].nunique()),
                        "messages": int(len(frame)), "control_windows": int(frame.loc[~frame["away"], ["absence_id", "window"]]
                                                                               .drop_duplicates().shape[0])}
    report["away_effect"] = away_effect(frame, "answered", draws)
    report["H1"] = logistic(frame, SIGNALS + BASELINES, "answered", tests, draws)
    report["H1_cross_validated_log_loss"] = cross_validated(frame, "answered")
    ranked = frame.merge(rank[["person", "level"]], on="person", how="inner")
    if ranked["person"].nunique() >= 10:
        levels = ranked.drop_duplicates("absence_id")["level"]       # standardized over absences, like the rest
        ranked["z_rank"] = (ranked["level"] - levels.mean()) / levels.std(ddof=0)
        report["H1_with_rank"] = logistic(ranked, SIGNALS + BASELINES + ["rank"], "answered", tests,
                                          person_draws(ranked, rng))
    else:
        report["H1_with_rank"] = {"error": f"only {ranked['person'].nunique()} people matched to the title list"}
    backup = frame.assign(z_names_backup=frame["names_backup"].astype(float))
    report["H2"] = logistic(backup, BASELINES + ["names_backup"], "answered", ["away:names_backup"], draws)
    people = people_effects(frame, rank, persons)
    people.to_csv(results / "analysis_people.csv", index=False)
    report["H3"] = {"people": int(len(people)), "file": "results/analysis_people.csv"}

    placebo = frame[frame["window"] != "away"].copy()
    placebo = placebo[placebo["absence_id"].isin(placebo.loc[placebo["window"] == "c2", "absence_id"])]
    placebo["away"] = placebo["window"] == "c2"
    has = placebo.groupby("absence_id")["away"].agg(["any", "all"])
    placebo = placebo[placebo["absence_id"].isin(has.index[has["any"] & ~has["all"]])].reset_index(drop=True)
    report["placebo"] = away_effect(placebo, "answered", person_draws(placebo, rng))

    window_out = pd.read_parquet(data / "window_outcomes.parquet")
    window_out = window_out[window_out["absence_id"].isin(frame["absence_id"])]
    report["secondary"] = secondary(window_out, rng)

    sensitivity = {}
    runs = {"auto_replies": ("auto_replies", "answered", 56, None), "high_confidence_links": ("main", "answered_high", 56, None),
            "reply_within_48h": ("main", "answered_48", 56, "eligible_48"), "threshold_10": ("threshold_10", "answered", 56, None),
            "signals_26_weeks": ("main", "answered", 182, None), "post_filing": ("post_filing", "answered", 56, None),
            "year_end": ("year_end", "answered", 56, None)}
    for name, (run, outcome, days, eligible) in runs.items():
        f = assemble(windows, messages, signals, run, days) if days == 56 or run == "main" else None
        if eligible:
            f = f[f[eligible]].reset_index(drop=True)
        if f is None or f.empty or f["person"].nunique() < 5:
            sensitivity[name] = {"error": "too few absences"}
            continue
        d = person_draws(f, rng)
        sensitivity[name] = {"away_effect": away_effect(f, outcome, d),
                             "H1": logistic(f, SIGNALS + BASELINES, outcome, tests, d)}
    report["sensitivity"] = sensitivity
    results.mkdir(parents=True, exist_ok=True)
    (results / "analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("sample", "away_effect")}, indent=2))


if __name__ == "__main__":
    main()
