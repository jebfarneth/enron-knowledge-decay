import pandas as pd

from enron_importance.gold_standard import dominance_pairs, match_people


def employee(uid, node, position="Manager", edges=(), email=True, mailbox=False):
    doc = {"_id": f"id{uid}", "position": position,
           "position_nodes": [{"uid": node, "incident_edges": [{"ffrom": a, "to": b, "relationship": "r"} for a, b in edges]}],
           "email_addresses": [f"p{uid}@enron.com"]}
    if email:
        doc["uid"] = uid
    if mailbox:
        doc["mailboxes"] = ["x"]
    return doc


def test_dominance_is_the_closure_through_units_among_emailers():
    unit = {"_id": "u", "position_nodes": [{"uid": "U1", "incident_edges": [{"ffrom": "U1", "to": "N2", "relationship": "contains"},
                                                                           {"ffrom": "U1", "to": "N3", "relationship": "contains"}]}]}
    entities = [
        employee(1, "N1", "VP", edges=[("N1", "U1")], mailbox=True),   # manages the unit holding 2 and 3
        employee(2, "N2", edges=[("N2", "N4")]),                        # supervises 4
        employee(3, "N3", email=False, edges=[("N3", "N5")]),           # no email, but still passes dominance to 5
        employee(4, "N4"),
        employee(5, "N5"),
        unit,
    ]
    employees, pairs = dominance_pairs(entities)
    assert set(zip(pairs["dominant"], pairs["subordinate"])) == {("1", "2"), ("1", "4"), ("2", "4"), ("1", "5")}
    assert employees.set_index("gold_id").loc["1", "custodian"]


def test_contradictory_pairs_are_dropped():
    entities = [employee(1, "N1", edges=[("N1", "N2")]), employee(2, "N2", edges=[("N2", "N1")])]
    _, pairs = dominance_pairs(entities)
    assert pairs.empty


def test_employees_match_through_their_addresses():
    employees = pd.DataFrame({"addresses": [["p1@enron.com", "p1@aol.com"], ["kay.mann@enron.com"], []]})
    identities = pd.DataFrame({"address": ["p1@enron.com"], "person_key": ["ann lee"], "entity_type": ["person"]})
    identities = pd.concat([identities, pd.DataFrame({"address": ["x@enron.com"], "person_key": ["kay mann"], "entity_type": ["person"]})])
    matched = match_people(employees, identities)
    assert list(matched[:2]) == ["ann lee", "kay mann"] and pd.isna(matched[2])


def test_a_resolved_person_beats_an_unused_alias_address():
    employees = pd.DataFrame({"addresses": [["sabraham@enron.com", "sunil.abraham@enron.com"]]})
    identities = pd.DataFrame({"address": ["sunil.abraham@enron.com"], "person_key": ["sunil abraham"], "entity_type": ["person"]})
    assert list(match_people(employees, identities, {"sunil abraham"})) == ["sunil abraham"]
    only_aliases = pd.DataFrame({"addresses": [["zz@enron.com", "aa@enron.com"]]})
    assert list(match_people(only_aliases, identities, {"zz@enron.com"})) == ["zz@enron.com"]
