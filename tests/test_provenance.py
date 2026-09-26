import json

import pytest

from enron_importance import provenance
from enron_importance.provenance import STAGES, output_path, record_stage, stale_reasons


@pytest.fixture
def config(tmp_path, monkeypatch):
    for name, text in [("uv.lock", "lock"), ("labels.json", "labels")]:
        (tmp_path / name).write_text(text)
    monkeypatch.setattr(provenance, "LOCKFILE", tmp_path / "uv.lock")
    monkeypatch.setattr(provenance, "THREAD_LABELS", tmp_path / "labels.json")
    model = tmp_path / "model"
    model.mkdir()
    (model / "weights").write_text("w")
    monkeypatch.setattr(provenance, "model_directory", lambda name="en_core_web_sm": model)
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "corpus.tar.gz").write_text("corpus")
    return {"paths": {kind: tmp_path / kind for kind in ["raw", "interim", "processed", "results", "figures"]}, "seed": 1,
            "corpus": {"filename": "corpus.tar.gz"}}


def build(config, stages=None):
    for stage in stages or STAGES:
        for output in STAGES[stage][1]:
            path = output_path(config, output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{stage} {output}")
        record_stage(config, stage)


def test_a_complete_run_in_order_is_current(config):
    build(config)
    assert stale_reasons(config) == []


@pytest.mark.parametrize("output", [o for _, outputs in STAGES.values() for o in outputs])
def test_every_declared_output_is_checked(config, output):
    build(config)
    output_path(config, output).write_text("altered")
    assert any(output in reason for reason in stale_reasons(config))
    output_path(config, output).unlink()
    assert any(output in reason for reason in stale_reasons(config))


def test_a_stage_rebuilt_after_its_readers_makes_them_stale(config):
    build(config)
    build(config, ["identity"])
    reasons = stale_reasons(config)
    assert "threads: built before identity was rebuilt" in reasons and "rank: built before identity was rebuilt" in reasons
    assert not any(r.startswith("crosscheck") for r in reasons)   # reads only prepare


def test_a_missing_or_malformed_manifest_is_never_current(config):
    assert stale_reasons(config) == ["no manifest: the generated data was not recorded by the pipeline stages"]
    build(config)
    path = config["paths"]["processed"] / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["stages"]["network"]["outputs"] = {}
    del manifest["stages"]["threadcheck"]
    path.write_text(json.dumps(manifest))
    reasons = stale_reasons(config)
    assert "network: recorded outputs differ from the declared ones" in reasons and "threadcheck: not recorded" in reasons
    path.write_text("not json")
    assert stale_reasons(config) == ["the manifest is unreadable"]


def test_code_and_configuration_changes_make_every_stage_stale(config, monkeypatch):
    build(config)
    config["seed"] = 2
    assert sum("different configuration" in r for r in stale_reasons(config)) == len(STAGES)
    config["seed"] = 1
    monkeypatch.setattr(provenance, "code_hash", lambda *names: "other")
    assert sum("different code" in r for r in stale_reasons(config)) == len(STAGES)


def test_skipping_the_gold_stages_removes_their_outputs(config):
    build(config)
    record_stage(config, "gold", skipped=True)
    assert not any(output_path(config, o).exists() for o in STAGES["gold"][1])
    assert "goldeval: built before gold was rebuilt" in stale_reasons(config)
    build(config, ["goldeval"])                       # results made without gold pairs
    assert "goldeval: built although gold was skipped" in stale_reasons(config)
    record_stage(config, "goldeval", skipped=True)
    assert not any(output_path(config, o).exists() for o in STAGES["goldeval"][1])
    build(config, ["evaluate", "figures.baselines"])
    assert stale_reasons(config) == []
    output_path(config, "results/gold_standard_paired.csv").write_text("left over")
    assert any("earlier outputs remain" in r for r in stale_reasons(config))


def test_only_the_gold_stages_may_be_skipped(config):
    build(config)
    record_stage(config, "network", skipped=True)
    assert "network: skipped" in stale_reasons(config)


def test_a_stage_must_write_every_declared_output(config):
    with pytest.raises(FileNotFoundError):
        record_stage(config, "threads")


@pytest.mark.parametrize("path, stages", [
    ("uv.lock", list(STAGES)),                       # the lockfile is an input of every stage
    ("labels.json", ["threadcheck"]),                # the labelled thread sample
    ("model/weights", ["mentions"]),                 # the NER model files
    ("raw/corpus.tar.gz", ["prepare"]),              # the raw corpus
])
def test_a_changed_input_makes_its_stages_stale(config, tmp_path, path, stages):
    build(config)
    (tmp_path / path).write_text("changed")
    stale = {r.split(":")[0] for r in stale_reasons(config) if "input" in r}
    assert stale == set(stages)


def test_a_different_python_makes_every_stage_stale(config):
    build(config)
    path = config["paths"]["processed"] / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["stages"]["rank"]["python"] = "3.11.0"
    path.write_text(json.dumps(manifest))
    assert stale_reasons(config) == ["rank: built with Python 3.11.0"]


def test_a_partial_check_also_checks_everything_upstream(config):
    build(config)
    output_path(config, "processed/centrality.parquet").write_text("damaged")
    assert any("centrality.parquet" in r for r in stale_reasons(config, ["figures.baselines"]))
    assert stale_reasons(config, ["crosscheck"]) == []   # reads only prepare
