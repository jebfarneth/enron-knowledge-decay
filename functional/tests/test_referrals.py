import pytest

from enron_functional.referrals import find_referral


@pytest.mark.parametrize("text, mention", [
    ("Thanks for the note. Please check with Sara Shackleton on the ISDA.", "Sara Shackleton"),
    ("Ask Kim about the storage numbers.", "Kim"),
    ("You should talk to Mark before Friday.", "Mark"),
    ("I'm not sure, but Tana will know.", "Tana"),
    ("For credit questions, Bill is the best person.", "Bill"),
    ("Not my deal; feel free to get with Louise on it.", "Louise"),
])
def test_referrals(text, mention):
    assert find_referral(text, mention) is not None


@pytest.mark.parametrize("text, mention", [
    ("I talked to Sara yesterday about the ISDA.", "Sara"),
    ("Please see Mark's memo below.", "Mark"),
    ("Kim and I will meet on Friday.", "Kim"),
    ("I will call Louise tomorrow.", "Louise"),
    ("Thanks, Tana.", "Tana"),
])
def test_not_referrals(text, mention):
    assert find_referral(text, mention) is None


@pytest.mark.parametrize("text, mention, person", [
    ("Once Mark knows the number, he will leave it with his assistant.", "Mark", "mark haedicke"),
    ("SEE YA!!!", "YA", "yao apasu"),
    ("Please see Jennifer Fraser's memo below.", "Jennifer Fraser's", "jennifer fraser"),
    ("The Centre cannot see the roles Wade is handling.", "Wade", "wade cline"),
    ("Please contact Tracy Warner, who now runs recruiting.", "Tracy", "tracy geaccone"),
])
def test_development_sample_false_referrals(text, mention, person):
    assert find_referral(text, mention, person) is None


def test_a_first_name_followed_by_the_right_surname_or_a_phone_number_is_kept():
    assert find_referral("Please contact Tracy Geaccone with questions.", "Tracy", "tracy geaccone")
    assert find_referral("Please contact Sarita at 5-8232.", "Sarita", "sarita garza")
