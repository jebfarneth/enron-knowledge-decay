import pandas as pd
import pytest

from enron_importance.network import build_edges, centrality


def msg(sender, to, cc=()):
    return {"sender_person": sender, "to": list(to), "cc": list(cc)}


PEOPLE = {"a@enron.com": "a", "a2@enron.com": "a", "b@enron.com": "b", "c@enron.com": "c", "d@enron.com": "d",
          "no.address@enron.com": None}


def test_broadcasts_are_split_and_aliases_merge():
    messages = pd.DataFrame([
        msg("a", ["b@enron.com", "c@enron.com", "d@enron.com", "x@aol.com"]),
        msg("a", ["b@enron.com", "a2@enron.com"]),   # a2 is a's alias: a self-copy
        msg("b", ["a@enron.com"], cc=["b@enron.com"]),  # self-copy ignored
    ])
    edges, sent = build_edges(messages, lambda r: PEOPLE.get(r, r), "enron.com")
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


def test_placeholders_and_unknown_senders_are_dropped_and_counts_are_integers():
    messages = pd.DataFrame([
        msg("a", ["no.address@enron.com"]),        # only recipient is a placeholder
        msg(None, ["a@enron.com"]),                # sender unknown
        msg("a", ["b@enron.com", "c@enron.com", "d@enron.com"]),
        msg("a", ["e@enron.com"]),                 # unresolved recipient address stays a node
    ])
    edges, sent = build_edges(messages, lambda r: PEOPLE.get(r, r), "enron.com")
    assert sent.to_dict() == {"a": 2}
    assert set(edges["target"]) == {"b", "c", "d", "e@enron.com"}
    measures = centrality(edges, sent).set_index("person_key")
    assert measures.loc["a", "out_strength"] == 2 and measures.loc["b", "out_strength"] == 0


def test_recipient_limit_skips_broadcasts():
    messages = pd.DataFrame([msg("a", ["b@enron.com", "c@enron.com", "d@enron.com"]), msg("a", ["b@enron.com"])])
    edges, sent = build_edges(messages, lambda r: PEOPLE.get(r, r), "enron.com", max_recipients=2)
    assert list(zip(edges["source"], edges["target"])) == [("a", "b")] and sent["a"] == 1


def test_edges_come_out_sorted_whatever_the_input_order():
    rows = [msg("b", ["a@enron.com"]), msg("a", ["d@enron.com", "c@enron.com"])]
    first, _ = build_edges(pd.DataFrame(rows), lambda r: PEOPLE.get(r, r), "enron.com")
    second, _ = build_edges(pd.DataFrame(rows[::-1]), lambda r: PEOPLE.get(r, r), "enron.com")
    assert first.equals(second)
    assert list(zip(first["source"], first["target"])) == [("a", "c"), ("a", "d"), ("b", "a")]


def test_people_from_other_copies_join_the_targets():
    messages = pd.DataFrame([{**msg("a", ["b@enron.com"]), "recipient_extra": ["c"]}])
    edges, sent = build_edges(messages, lambda r: PEOPLE.get(r, r), "enron.com")
    assert set(zip(edges["source"], edges["target"])) == {("a", "b"), ("a", "c")}
    assert edges.set_index("target").loc["c", "weight"] == 0.5


def test_second_spellings_of_a_recipient_are_not_added():
    from enron_importance.identity import extra_recipients
    people = {"michael brown", "christopher calger", "carla hoffman", "mark a palmer"}
    resolve = {".brown@enron.com": ".brown@enron.com", "michael.brown@enron.com": "michael brown",
               "f..calger@enron.com": "christopher calger", "f..carla@enron.com": "carla hoffman",
               "mark.a.palmer@enron.com": "mark a palmer"}.get
    assert extra_recipients(["michael brown"], [".brown@enron.com"], resolve, people) == []
    assert extra_recipients([".brown@enron.com"], ["michael.brown@enron.com"], resolve, people) == []
    assert extra_recipients(["carla hoffman"], ["f..calger@enron.com"], resolve, people) == ["christopher calger"]
    assert extra_recipients(["mark palmer"], ["mark.a.palmer@enron.com"], resolve, people) == []


def test_surname_first_addresses_and_unresolved_extras_are_not_added():
    from enron_importance.identity import extra_recipients
    people = {"george phillips", "ann lee"}
    resolve = {"george.phillips@enron.com": "george phillips", "x.unknown@enron.com": "x.unknown@enron.com",
               "ann.lee@enron.com": "ann lee"}.get
    assert extra_recipients(["phillips.george@enron.com"], ["george.phillips@enron.com"], resolve, people) == []
    assert extra_recipients(["bob@enron.com"], ["x.unknown@enron.com"], resolve, people) == []   # not a person
    assert extra_recipients(["bob@enron.com"], ["ann.lee@enron.com"], resolve, people) == ["ann lee"]
