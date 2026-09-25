import pandas as pd

from enron_importance.identity import build_identities, normalize_name


def test_display_name_shapes_normalize_to_one_key():
    assert normalize_name("Christopher F Calger") == "christopher calger"
    assert normalize_name("Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>") == "christopher calger"
    assert normalize_name("Christopher F Calger <Christopher F Calger/PDX/ECT@ECT>") == "christopher calger"
    assert normalize_name("Allen, Phillip K. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=PALLEN>") == "phillip allen"
    assert normalize_name("O'Neal, D'Arcy") == "d'arcy o'neal"


def test_unusable_display_names_return_none():
    for value in [None, float("nan"), "", "jeff.dasovich@enron.com", "Enron", "J"]:
        assert normalize_name(value) is None, value


def test_alias_addresses_merge_into_one_person():
    messages = pd.DataFrame([
        {"sender": "christopher.calger@enron.com", "x_from": "Christopher F Calger"},
        {"sender": "christopher.calger@enron.com", "x_from": "Christopher F Calger"},
        {"sender": "f..calger@enron.com", "x_from": "Calger, Christopher F. </O=ENRON/OU=NA/CN=RECIPIENTS/CN=CCALGER>"},
        {"sender": "anon@enron.com", "x_from": None},
        {"sender": "outside@aol.com", "x_from": "Somebody Else"},
    ])
    table = build_identities(messages, "enron.com").set_index("address")
    assert table.loc["christopher.calger@enron.com", "person_key"] == table.loc["f..calger@enron.com", "person_key"] == "christopher calger"
    assert table.loc["anon@enron.com", "person_key"] == "anon@enron.com"
    assert "outside@aol.com" not in table.index
    assert table.loc["f..calger@enron.com", "display_name"] == "Christopher Calger"
