import pandas as pd

from enron_importance.gold_standard import dominance_pairs, match_people, mixed_positions, principal_name


def employee(uid, node, position="Manager", edges=(), email=True, mailbox=None, names=None, addresses=None,
             extra_nodes=(), top_level_edges=()):
    nodes = [{"uid": node, "position": position,
              "incident_edges": [{"ffrom": a, "to": b, "relationship": "r"} for a, b in edges]}]
    nodes += [{"uid": n, "position": p, "incident_edges": []} for n, p in extra_nodes]
    doc = {"_id": f"id{uid}", "position": position, "position_nodes": nodes,
           "incident_edges": [{"ffrom": a, "to": b, "relationship": "r"} for a, b in top_level_edges],
           "email_addresses": addresses if addresses is not None else [f"p{uid}@enron.com"],
           "email_names": names or [f"Person Number{uid}"]}
    if email:
        doc["uid"] = uid
    if mailbox:
        doc["mailboxes"] = [mailbox]
    return doc


def unit(node, children):
    return {"_id": f"u{node}", "position_nodes": [{"uid": node, "incident_edges": [
        {"ffrom": node, "to": c, "relationship": "contains"} for c in children]}]}


def pairs_of(frame):
    return set(zip(frame["dominant"], frame["subordinate"]))


def test_dominance_is_the_closure_through_units_among_emailers():
    entities = [
        employee(1, "N1", "VP", edges=[("N1", "U1")], mailbox="one-p"),  # manages the unit holding 2 and 3
        employee(2, "N2", edges=[("N2", "N4")]),                        # supervises 4
        employee(3, "N3", email=False, edges=[("N3", "N5")]),           # no email, but still passes dominance to 5
        employee(4, "N4"),
        employee(5, "N5"),
        unit("U1", ["N2", "N3"]),
    ]
    employees, pairs, _ = dominance_pairs(entities)
    assert pairs_of(pairs) == {("1", "2"), ("1", "4"), ("2", "4"), ("1", "5")}
    assert employees.set_index("gold_id").loc["1", "custodian"]


def test_edges_stored_only_at_the_top_level_of_a_record_are_used():
    entities = [employee(1, "N1", top_level_edges=[("N1", "N2")]), employee(2, "N2")]
    _, pairs, _ = dominance_pairs(entities)
    assert pairs_of(pairs) == {("1", "2")}


def test_every_position_of_a_record_counts_and_alternatives_differ():
    # 1 holds N1 and N1b; N1b supervises 2. Closing positions first keeps 1 over 2 as well.
    entities = [employee(1, "N1", extra_nodes=[("N1b", "Director")], top_level_edges=[("N1b", "N2")]),
                employee(2, "N2", edges=[("N2", "N3")]), employee(3, "N3")]
    _, pairs, alternatives = dominance_pairs(entities)
    assert pairs_of(pairs) == {("1", "2"), ("1", "3"), ("2", "3")}
    assert pairs_of(alternatives["positions closed before mapping"]) == {("1", "2"), ("1", "3"), ("2", "3")}


def test_contradictory_pairs_are_dropped_and_cycle_arcs_can_be_removed_first():
    # 1 and 2 dominate each other through different positions; both dominate 3.
    entities = [employee(1, "N1", edges=[("N1", "N2")], extra_nodes=[("N1b", "Chair")]),
                employee(2, "N2", edges=[("N2", "N1b"), ("N2", "N3")]), employee(3, "N3")]
    _, pairs, alternatives = dominance_pairs(entities)
    assert ("1", "2") not in pairs_of(pairs) and ("2", "1") not in pairs_of(pairs)
    assert {("1", "3"), ("2", "3")} <= pairs_of(pairs)
    assert pairs_of(alternatives["cycle arcs removed before closure"]) == {("2", "3")}


def test_assistant_positions_mixed_with_other_titles_are_flagged():
    assert mixed_positions(["Managing Director", "Sr Administrative Assistant", "VP"])
    assert mixed_positions(["President & CEO", "Executive Assistant"])
    assert not mixed_positions(["Asst General Counsel", "VP, Assistant General Counsel"])
    assert not mixed_positions(["Administrative Assistant II", "?"])
    assert not mixed_positions(["Corporate Secretary", "VP"])


def test_principal_name_uses_the_mailbox_then_frequency():
    names = ["Phillip K Allen", "Ina Rangel", "Phillip Allen", "Ina K Rangel", "pallen@enron.com"]
    assert principal_name(names, ["Allen-P"]) == "phillip allen"
    assert principal_name(names, []) is None                         # tied without a mailbox
    assert principal_name(["Lou Pai", "Lou D Pai", "avid Oxley"], []) == "lou pai"
    assert principal_name(["Mike McConnell", "Cathy Phillips"], ["MCCONNELL-M"]) == "michael mcconnell"


def matched(employees, identities, nodes, types=None, aliases=None):
    return match_people(pd.DataFrame(employees), identities, set(nodes), aliases or {}, types or {})


IDENTITIES = pd.DataFrame({
    "address": ["phillip.allen@enron.com", "ina.rangel@enron.com", "jlavora@enron.com"],
    "person_key": ["phillip allen", "ina rangel", "john lavorato"],
    "entity_type": ["person", "person", "person"],
})


def test_executives_are_matched_by_name_not_by_their_assistants_addresses():
    rows = [
        {"names": ["Phillip K Allen", "Ina Rangel", "Phillip Allen", "Ina K Rangel"], "mailboxes": ["Allen-P"],
         "addresses": ["ina.rangel@enron.com", "irangel@enron.com"]},
        {"names": ["John Lavorato", "Angela McCulloch", "John J Lavorato"], "mailboxes": ["LAVORATO-J"],
         "addresses": ["amccull@enron.com", "jlavora@enron.com"]},
    ]
    out = matched(rows, IDENTITIES, {"phillip allen", "ina rangel", "john lavorato"})
    assert list(out["person_key"]) == ["phillip allen", "john lavorato"]
    assert list(out["match_status"]) == ["name", "name+address"]


def test_address_nodes_ambiguous_keys_and_absent_people():
    rows = [
        {"names": ["Lou Pai", "Lou D Pai"], "mailboxes": [], "addresses": ["29bd17ed@enron.com"]},
        {"names": ["Thomas E White", "Tom White", "Thomas White"], "mailboxes": [], "addresses": []},
        {"names": ["Mark Palmer", "Mark A Palmer"], "mailboxes": [], "addresses": []},
        {"names": ["Nobody Here"], "mailboxes": [], "addresses": []},
        {"names": ["Michael Anderson", "Pamela Anderson"], "mailboxes": [], "addresses": []},
    ]
    nodes = {"lou.pai@enron.com", "thomas.white@enron.com", "tom.white@enron.com", "mark palmer"}
    out = matched(rows, IDENTITIES, nodes, types={"mark palmer": "ambiguous"})
    assert list(out["person_key"].fillna("-")) == ["lou.pai@enron.com", "thomas.white@enron.com", "-", "-", "-"]
    assert list(out["match_status"]) == ["address node", "address node", "ambiguous", "absent", "ambiguous"]
