import pandas as pd

from enron_importance.identity import entity_type, normalize_name, resolve_people, resolve_recipient


def test_display_name_shapes_normalize_to_one_key():
    assert normalize_name("Christopher F Calger") == "christopher calger"
    assert normalize_name("Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>") == "christopher calger"
    assert normalize_name("Christopher F Calger <Christopher F Calger/PDX/ECT@ECT>") == "christopher calger"
    assert normalize_name("Allen, Phillip K. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=PALLEN>") == "phillip allen"
    assert normalize_name("O'Neal, D'Arcy") == normalize_name("ONeal, DArcy") == "darcy oneal"


def test_a_job_title_after_a_comma_is_not_a_first_name():
    assert normalize_name("George Wasaff, Global Strategic Sourcing <George Wasaff, Global Strategic Sourcing@ENRON>") == "george wasaff"
    assert normalize_name("Robert Knight, Director Voice Operations & Trading Technology") == "robert knight"
    assert normalize_name("Davis, Mark Dana") == "mark davis"
    assert normalize_name("Baughman Jr., Don") == "don baughman"


def test_shared_mailboxes_and_rooms_are_roles():
    room = normalize_name("Conf. Room ECN2760 </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MBX_CRECN2760>")
    office = normalize_name("Legal - James Derrick Jr. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MBX_ANNCLEGAL>")
    assert entity_type(room) == entity_type(office) == "role"
    assert entity_type(normalize_name("Conf. Room ECN2760")) == "role"


def test_unusable_display_names_return_none():
    for value in [None, float("nan"), "", "jeff.dasovich@enron.com", "Enron", "J"]:
        assert normalize_name(value) is None, value


def test_generational_suffixes_are_dropped():
    assert normalize_name("Baughman Jr., Don </O=ENRON/OU=NA/CN=RECIPIENTS/CN=DBAUGHM>") == "don baughman"
    assert normalize_name("Derrick Jr., James </O=ENRON/OU=NA/CN=RECIPIENTS/CN=JDERRIC>") == "james derrick"


def test_nicknames_resolve_to_one_person():
    assert normalize_name("Tim Belden") == normalize_name("Timothy Belden") == "timothy belden"
    assert normalize_name("Schwieger, Jim") == normalize_name("James Schwieger") == "james schwieger"
    assert normalize_name("Mike Swerzbin") == "michael swerzbin"


def test_numbered_role_mailboxes_stay_distinct():
    assert normalize_name("Legal Temp 1") == "legal temp 1"
    assert normalize_name("Legal Temp 7") == "legal temp 7"
    assert entity_type("legal temp 1") == entity_type("office of the chairman") == "role"
    assert entity_type("kay mann") == "person"


def resolve(rows, placeholders=()):
    messages = pd.DataFrame(rows, columns=["sender", "x_from"])
    people, table, aliases, _ = resolve_people(messages, "enron.com", list(placeholders), min_initial_support=2,
                                               min_initialled=2)
    return people, table.set_index("address"), aliases


def test_alias_addresses_merge_into_one_person():
    people, table, _ = resolve([
        ("christopher.calger@enron.com", "Christopher F Calger"),
        ("christopher.calger@enron.com", "Christopher F Calger"),
        ("f..calger@enron.com", "Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>"),
        ("anon@enron.com", None),
        ("outside@aol.com", "Somebody Else"),
    ])
    assert table.loc["christopher.calger@enron.com", "person_key"] == table.loc["f..calger@enron.com", "person_key"] == "christopher calger"
    assert table.loc["anon@enron.com", "person_key"] == "anon@enron.com"
    assert table.loc["anon@enron.com", "entity_type"] == "address"
    assert "outside@aol.com" not in table.index
    assert people.iloc[4] is None or pd.isna(people.iloc[4])


def test_address_takes_its_most_common_name_not_its_first():
    _, table, _ = resolve([
        ("dana.davis@enron.com", "Mark Davis"),
        ("dana.davis@enron.com", "Dana Davis"),
        ("dana.davis@enron.com", "Dana Davis"),
    ])
    assert table.loc["dana.davis@enron.com", "person_key"] == "dana davis"


def test_each_message_is_attributed_by_its_own_display_name():
    people, _, _ = resolve([
        ("dana.davis@enron.com", "Dana Davis"),
        ("dana.davis@enron.com", "Dana Davis"),
        ("dana.davis@enron.com", "Mark Davis"),
        ("dana.davis@enron.com", None),
    ])
    assert list(people) == ["dana davis", "dana davis", "mark davis", "dana davis"]


def test_placeholder_address_is_never_a_person():
    people, table, _ = resolve([
        ("no.address@enron.com", "Don Miller"),
        ("no.address@enron.com", "Public Relations@ENRON"),
        ("no.address@enron.com", "Corporate Security@ENRON"),
        ("don.miller@enron.com", "Miller, Don"),
    ], placeholders=["no.address@enron.com"])
    assert list(people.iloc[:3].fillna("unknown")) == ["don miller", "unknown", "unknown"]
    assert pd.isna(table.loc["no.address@enron.com", "person_key"])
    assert table.loc["no.address@enron.com", "entity_type"] == "placeholder"
    address_person = dict(zip(table.index, table["person_key"]))
    assert resolve_recipient("no.address@enron.com", address_person, {"don miller"}) is None


def test_address_shared_by_several_named_senders_becomes_a_placeholder():
    rows = [("shared@enron.com", name) for name in ["Ann Lee"] * 3 + ["Bo Chan"] * 3] + [("shared@enron.com", None)] * 4
    _, table, _ = resolve(rows)
    assert table.loc["shared@enron.com", "entity_type"] == "placeholder"


def test_numbered_temp_accounts_are_not_merged():
    _, table, _ = resolve([("legal.1@enron.com", "Legal Temp 1"), ("legal.7@enron.com", "Legal Temp 7")])
    assert table.loc["legal.1@enron.com", "person_key"] != table.loc["legal.7@enron.com", "person_key"]


def test_homonyms_with_different_middle_initials_are_split():
    people, table, _ = resolve([
        (".taylor@enron.com", "Taylor, Mark E (Legal) </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MTAYLO1>"),
        (".taylor@enron.com", "Taylor, Mark E (Legal) </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MTAYLO1>"),
        ("a.taylor@enron.com", "Mark A Taylor"),
        ("a.taylor@enron.com", "Mark A Taylor"),
        ("mark.taylor@enron.com", "Mark E Taylor"),
        ("mark.taylor@enron.com", "Mark E Taylor"),
        ("mark.taylor@enron.com", "Mark E Taylor"),
        ("mark.taylor@enron.com", "Mark A Taylor"),
        ("mark.taylor@enron.com", "Mark Taylor"),
        ("x@enron.com", "Taylor, Mark </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MTAYLO1>"),
    ])
    assert table.loc[".taylor@enron.com", "person_key"] == "mark e taylor"
    assert table.loc["a.taylor@enron.com", "person_key"] == "mark a taylor"
    # Uninitialled messages take the initial their address or directory ID uses.
    assert people.iloc[7] == "mark a taylor"
    assert people.iloc[8] == "mark e taylor"
    assert people.iloc[9] == "mark e taylor"


def test_names_sharing_a_directory_id_and_surname_merge():
    people, _, aliases = resolve([
        ("albert.meyers@enron.com", "Meyers, Albert </O=ENRON/OU=NA/CN=RECIPIENTS/CN=BMEYERS>"),
        ("bert.meyers@enron.com", "Meyers, Bert </O=ENRON/OU=NA/CN=RECIPIENTS/CN=BMEYERS>"),
        ("bert.meyers@enron.com", "Meyers, Bert </O=ENRON/OU=NA/CN=RECIPIENTS/CN=BMEYERS>"),
        ("kay.mann@enron.com", "Mann, Kay </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MMANNING>"),
        ("marykay.manning@enron.com", "Manning, MaryKay </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MMANNING>"),
        ("a@enron.com", "Jones, Ann </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MBX_ANNC>"),
        ("b@enron.com", "Jones, Bea </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MBX_ANNC>"),
    ])
    assert set(people.iloc[:3]) == {"albert meyers"}
    assert aliases == {"bert meyers": "albert meyers"}
    assert people.iloc[3] == "kay mann" and people.iloc[4] == "marykay manning"
    assert people.iloc[5] != people.iloc[6]


def test_recipient_only_addresses_resolve_by_first_last_pattern_only():
    known = {"berney aucoin"}
    assert resolve_recipient("berney.aucoin@enron.com", {}, known) == "berney aucoin"
    assert resolve_recipient("cliff.baxter@enron.com", {}, known) == "cliff.baxter@enron.com"
    assert entity_type("center.dl-portland@enron.com") == "list"
    assert entity_type("cliff.baxter@enron.com") == "address"


def test_a_go_by_middle_name_joins_the_person_it_names():
    people, _, aliases = resolve([
        ("dana.davis@enron.com", "Dana Davis"),
        ("dana.davis@enron.com", "Davis, Dana </O=ENRON/OU=NA/CN=RECIPIENTS/CN=DDAVIS>"),
        ("dana.davis@enron.com", "Davis, Mark Dana </O=ENRON/OU=NA/CN=RECIPIENTS/CN=MDAVIS>"),
        ("mark.davis@enron.com", "Davis, Mark Dana"),
        ("mark.davis@enron.com", "Davis, Mark Dana"),
        ("other.davis@enron.com", "Mark Davis"),     # a different Mark Davis never uses the name Dana
    ])
    assert list(people.iloc[:5]) == ["dana davis"] * 5
    assert people.iloc[5] == "mark davis" and "mark davis" not in aliases


def test_a_few_initialled_messages_do_not_assign_many_unmarked_ones():
    rows = ([(".palmer@enron.com", "Mark A Palmer")] * 3 + [("mark.palmer@enron.com", "Mark S Palmer")] * 3
            + [("mark.palmer@enron.com", "Mark Palmer")] * 20)
    messages = pd.DataFrame(rows, columns=["sender", "x_from"])
    people, _, _, types = resolve_people(messages, "enron.com", [], min_initial_support=2, min_initialled=5)
    assert set(people.iloc[6:]) == {"mark palmer"} and types["mark palmer"] == "ambiguous"


def test_initial_inference_boundaries():
    def assign(initialled_e, initialled_a, min_initialled):
        rows = ([("m.t@enron.com", "Mark E Taylor")] * initialled_e + [("m.t@enron.com", "Mark A Taylor")] * initialled_a
                + [("m.t@enron.com", "Mark Taylor")])
        people, *_ = resolve_people(pd.DataFrame(rows, columns=["sender", "x_from"]), "enron.com", [],
                                    min_initial_support=1, min_initialled=min_initialled)
        return people.iloc[-1]
    assert assign(2, 1, 3) == "mark e taylor"     # exactly two thirds, exactly the minimum
    assert assign(2, 1, 4) == "mark taylor"       # one initialled message short
    assert assign(3, 2, 5) == "mark taylor"       # 60% is under two thirds
