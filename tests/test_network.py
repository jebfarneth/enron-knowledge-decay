import pandas as pd
import pytest

from enron_importance.network import build_edges, centrality


def msg(sender, to, cc=()):
    return {"sender": sender, "to": list(to), "cc": list(cc)}


def test_broadcasts_are_split_and_aliases_merge():
    messages = pd.DataFrame([
        msg("a@enron.com", ["b@enron.com", "c@enron.com", "d@enron.com", "x@aol.com"]),
        msg("a2@enron.com", ["b@enron.com"]),   # alias of a
        msg("b@enron.com", ["a@enron.com"], cc=["b@enron.com"]),  # self-copy ignored
    ])
    edges = build_edges(messages, {"a@enron.com": "a", "a2@enron.com": "a", "b@enron.com": "b", "c@enron.com": "c", "d@enron.com": "d"}, "enron.com")
    table = edges.set_index(["source", "target"])
    assert table.loc[("a", "b"), "weight"] == pytest.approx(1 / 3 + 1)
    assert table.loc[("a", "b"), "messages"] == 2
    assert table.loc[("a", "c"), "weight"] == pytest.approx(1 / 3)
    assert table.loc[("b", "a"), "weight"] == 1
    assert ("b", "b") not in table.index and not edges["target"].str.contains("aol").any()


def test_star_centre_has_top_degree_and_betweenness():
    edges = pd.DataFrame([("hub", leaf, 1.0, 1) for leaf in "abcd"] + [("a", "b", 1.0, 1)],
                         columns=["source", "target", "weight", "messages"])
    measures = centrality(edges).set_index("person_key")
    assert measures["degree"].idxmax() == "hub" and measures.loc["hub", "degree"] == 4
    assert measures["betweenness"].idxmax() == "hub"
    # hub lies on the shortest path of every leaf pair except a-b (5 of 6 pairs).
    assert measures.loc["hub", "betweenness"] == pytest.approx(5)


def test_heavier_ties_are_shorter_paths():
    # a-b-c chain with a strong a-b tie and a weak direct a-c tie: the route
    # through b is shorter, so b carries the a-c path.
    edges = pd.DataFrame([("a", "b", 10.0, 1), ("b", "c", 10.0, 1), ("a", "c", 1.0, 1)],
                         columns=["source", "target", "weight", "messages"])
    measures = centrality(edges).set_index("person_key")
    assert measures.loc["b", "betweenness"] == pytest.approx(1)
