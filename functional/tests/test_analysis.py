import numpy as np
import pandas as pd
import pytest

from enron_functional.analysis import bootstrap_p, design, holm, people_effects, standardized


def test_holm_step_down():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adjusted == {"a": 0.03, "c": 0.06, "b": 0.06}


def test_bootstrap_p_is_two_sided():
    assert bootstrap_p(np.array([1.0, 2.0, 3.0, -1.0])) == pytest.approx(0.5)
    assert bootstrap_p(np.array([1.0, 2.0])) == 0.0


def test_counts_are_logged_and_everything_standardized_over_absences():
    sig = pd.DataFrame({"absence_id": [1, 2, 3], "pointed_to": [0, 0, 6], "topic_ownership": [0.1, 0.2, 0.3]})
    z = standardized(sig, ["pointed_to", "topic_ownership"])
    assert z["z_pointed_to"].mean() == pytest.approx(0) and z["z_pointed_to"].std(ddof=0) == pytest.approx(1)
    assert z["z_topic_ownership"].tolist() == pytest.approx([-1.2247, 0, 1.2247], abs=1e-4)


def test_design_has_each_moderator_and_its_away_interaction():
    frame = pd.DataFrame({"away": [True, False], "z_sent": [1.0, 2.0]})
    x, names = design(frame, ["sent"])
    assert names == ["const", "away", "sent", "away:sent"]
    assert x.tolist() == [[1, 1, 1, 1], [1, 0, 2, 0]]


def test_people_effects_shrink_toward_the_mean():
    rows = []
    for person, away_rate, control_rate in [("a", 0.0, 0.5), ("b", 0.4, 0.5), ("c", 0.5, 0.5)]:
        for away, rate in ((True, away_rate), (False, control_rate)):
            rows += [{"person": person, "away": away, "answered": i < rate * 20} for i in range(20)]
    out = people_effects(pd.DataFrame(rows), pd.DataFrame({"person": ["a"], "title": ["VP"], "level": [5]}),
                         {"a", "b", "c"}).set_index("person")
    assert out.loc["a", "away_effect"] == pytest.approx(-0.5)
    assert out.loc["a", "away_effect"] <= out.loc["a", "away_effect_shrunk"] <= out["away_effect"].mean()
    assert out.loc["a", "title"] == "VP"
