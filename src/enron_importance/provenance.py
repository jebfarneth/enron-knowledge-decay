"""Which code, configuration and upstream stages built each generated file.

Every stage ends with `record_stage(config, stage)`, which checksums the
stage's declared outputs into data/processed/manifest.json together with the
hashes of the package source and the configuration and a sequence number. A
stage that cannot run (the gold standard without the authors' release) is
recorded as skipped, and its declared outputs are deleted so earlier results
cannot outlive it.

Each stage also records the checksums of the files it reads besides earlier
stages' outputs (`stage_inputs`: the raw corpus, the title list, the gold
release, the labelled thread sample, the NER model files, and uv.lock for
every stage) and the Python version.

`stale_reasons(config)` certifies a complete run: every stage recorded, by
the current code, configuration, Python and inputs, after every stage it
reads from, with exactly its declared outputs, each unchanged since; a
skipped stage must be one allowed to skip, leave none of its outputs behind,
and take every stage that reads it along.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from .config import ROOT
from .download import sha256_of

PACKAGE = Path(__file__).resolve().parent
MANIFEST = "manifest.json"

# stage: (stages it reads from, outputs as "<paths key>/<file>")
STAGES: dict[str, tuple[tuple[str, ...], list[str]]] = {
    "prepare": ((), ["interim/messages_raw.parquet", "processed/messages.parquet", "processed/senders.parquet",
                     "processed/copies.parquet", "processed/funnel.json"]),
    "identity": (("prepare",), ["processed/identities.parquet", "processed/sender_people.parquet",
                                "processed/person_types.parquet", "processed/name_aliases.parquet",
                                "processed/person_text.json"]),
    "threads": (("prepare", "identity"), ["processed/links.parquet", "processed/links.json"]),
    "rank": (("identity",), ["processed/formal_rank.parquet"]),
    "network": (("prepare", "identity"), ["processed/edges.parquet", "processed/centrality.parquet"]),
    "mentions": (("prepare", "identity", "network"), ["processed/mentions.parquet", "processed/mention_centrality.parquet",
                                                      "processed/mention_tags.parquet", "results/mention_resolution.json"]),
    "gold": (("identity", "network"), ["processed/gold_employees.parquet", "processed/gold_pairs.parquet",
                                       "processed/gold_coverage.json"]),
    "goldeval": (("prepare", "network", "mentions", "gold"), ["results/baselines_gold_standard.csv",
                                                             "results/gold_standard_sensitivity.csv",
                                                             "results/gold_standard_paired.csv",
                                                             "results/gold_standard_coverage.json"]),
    "evaluate": (("prepare", "identity", "rank", "network", "mentions"), ["results/baselines_formal_rank.csv",
                                                                          "results/baselines_paired_differences.csv",
                                                                          "results/baselines_sensitivity.csv"]),
    "crosscheck": (("prepare",), ["results/cleaning_crosscheck.json", "results/cleaning_crosscheck_disagreements.csv"]),
    "threadcheck": (("threads",), ["results/thread_link_check.json"]),
    "figures.funnel": (("prepare",), ["figures/fig01_data_funnel.pdf", "figures/fig01_data_funnel.png"]),
    "figures.baselines": (("evaluate",), ["figures/fig06_baselines_formal_rank.pdf",
                                          "figures/fig06_baselines_formal_rank.png"]),
}
# Stages that need the private gold-standard release and may be recorded as skipped.
OPTIONAL = {"gold", "goldeval"}
FIELDS = {"seq", "skipped", "code_sha256", "config_sha256", "python", "inputs", "outputs"}
LOCKFILE = ROOT / "uv.lock"
THREAD_LABELS = ROOT / "audits" / "labels" / "thread_links_sample60.json"


def code_hash(*names: str) -> str:
    """SHA-256 over the named source files of this package (all of them if none given)."""
    files = [PACKAGE / name for name in names] if names else sorted(PACKAGE.rglob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(PACKAGE).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def config_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, default=str).encode()).hexdigest()


def tree_hash(directory: Path) -> str:
    """SHA-256 over every file under `directory`, by relative path and content."""
    digest = hashlib.sha256()
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        digest.update(path.relative_to(directory).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def model_directory(name: str = "en_core_web_sm") -> Path | None:
    spec = importlib.util.find_spec(name)
    return Path(spec.origin).parent if spec and spec.origin else None


def stage_inputs(config: dict, stage: str) -> dict[str, str | None]:
    """Checksums of the files `stage` reads besides earlier stages' outputs (None for a missing file)."""
    raw = Path(config["paths"]["raw"]) if "raw" in config["paths"] else None
    files: dict[str, Path | None] = {"uv.lock": LOCKFILE}
    named = {"prepare": ("corpus", "filename"), "rank": ("formal_rank", "filename"), "gold": ("gold_standard", "entities")}
    if stage in named and raw is not None and named[stage][0] in config:
        section, key = named[stage]
        files[f"raw/{config[section][key]}"] = raw / config[section][key]
    if stage == "threadcheck":
        files["audits/labels/thread_links_sample60.json"] = THREAD_LABELS
    inputs = {name: sha256_of(path) if path is not None and path.exists() else None for name, path in files.items()}
    if stage == "mentions":
        directory = model_directory()
        inputs["model/en_core_web_sm"] = tree_hash(directory) if directory else None
    return inputs


def output_path(config: dict, output: str) -> Path:
    kind, name = output.split("/", 1)
    return Path(config["paths"][kind]) / name


def _manifest_path(config: dict) -> Path:
    return Path(config["paths"]["processed"]) / MANIFEST


def record_stage(config: dict, stage: str, skipped: bool = False) -> dict:
    """Record `stage` as just built from the current code and configuration, or as skipped.

    Every declared output must exist (FileNotFoundError otherwise); a skipped
    stage's outputs are deleted.
    """
    _, outputs = STAGES[stage]
    if skipped:
        for output in outputs:
            output_path(config, output).unlink(missing_ok=True)
    else:
        missing = [o for o in outputs if not output_path(config, o).exists()]
        if missing:
            raise FileNotFoundError(f"{stage} did not write {missing}")
    path = _manifest_path(config)
    manifest = json.loads(path.read_text()) if path.exists() else {"stages": {}}
    seq = 1 + max((entry.get("seq", 0) for entry in manifest["stages"].values()), default=0)
    manifest["stages"][stage] = {
        "seq": seq, "skipped": skipped, "code_sha256": code_hash(), "config_sha256": config_hash(config),
        "python": sys.version.split()[0], "inputs": stage_inputs(config, stage),
        "outputs": {} if skipped else {o: sha256_of(output_path(config, o)) for o in outputs},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".part")
    partial.write_text(json.dumps(manifest, indent=2) + "\n")
    partial.replace(path)
    return manifest["stages"][stage]


def stale_reasons(config: dict, stages: list[str] | None = None) -> list[str]:
    """Why the generated data is not one complete, current run (empty if it is).

    `stages` limits the check to those stages and every stage they read from, directly or not;
    all by default.
    """
    path = _manifest_path(config)
    if not path.exists():
        return ["no manifest: the generated data was not recorded by the pipeline stages"]
    try:
        recorded = json.loads(path.read_text())["stages"]
    except (ValueError, KeyError, TypeError):
        return ["the manifest is unreadable"]
    code, configuration, python = code_hash(), config_hash(config), sys.version.split()[0]
    selected = set(stages or STAGES)
    while True:  # close the selection over what it reads from
        wider = selected | {upstream for stage in selected for upstream in STAGES[stage][0]}
        if wider == selected:
            break
        selected = wider
    reasons = []
    for stage in [s for s in STAGES if s in selected]:
        depends, outputs = STAGES[stage]
        entry = recorded.get(stage)
        if not isinstance(entry, dict) or not FIELDS <= set(entry):
            reasons.append(f"{stage}: not recorded")
            continue
        if entry["code_sha256"] != code:
            reasons.append(f"{stage}: built by different code")
        if entry["config_sha256"] != configuration:
            reasons.append(f"{stage}: built with a different configuration")
        if entry["python"] != python:
            reasons.append(f"{stage}: built with Python {entry['python']}")
        for name, digest in stage_inputs(config, stage).items():
            if entry["inputs"].get(name, "unrecorded") != digest:
                reasons.append(f"{stage}: input {name} changed since it was built")
        for upstream in depends:
            before = recorded.get(upstream)
            if not isinstance(before, dict) or not FIELDS <= set(before):
                reasons.append(f"{stage}: reads {upstream}, which is not recorded")
            elif before["seq"] > entry["seq"]:
                reasons.append(f"{stage}: built before {upstream} was rebuilt")
            elif before["skipped"] and not entry["skipped"]:
                reasons.append(f"{stage}: built although {upstream} was skipped")
        if entry["skipped"]:
            if stage not in OPTIONAL:
                reasons.append(f"{stage}: skipped")
            left = [o for o in outputs if output_path(config, o).exists()]
            if left:
                reasons.append(f"{stage}: skipped, but earlier outputs remain: {left}")
            continue
        if sorted(entry["outputs"]) != sorted(outputs):
            reasons.append(f"{stage}: recorded outputs differ from the declared ones")
        for output in outputs:
            file = output_path(config, output)
            if not file.exists() or sha256_of(file) != entry["outputs"].get(output):
                reasons.append(f"{stage}: {output} changed or missing since it was built")
    return reasons
