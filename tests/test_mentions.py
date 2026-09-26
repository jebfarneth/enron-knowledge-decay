import pandas as pd

from enron_importance.mentions import Distances, compatible, mention_centrality, mention_links, name_index

PEOPLE = {"jeffrey skilling", "jeffrey dasovich", "mark e taylor", "kay mann", "sara shackleton", "jonah self"}


def test_mentions_match_full_first_last_nickname_and_initials():
    index = name_index(PEOPLE)
    assert compatible("Jeff", index) == {"jeffrey skilling", "jeffrey dasovich"}
    assert compatible("Skilling", index) == {"jeffrey skilling"}
    assert compatible("Jeff Skilling", index) == {"jeffrey skilling"}
    assert compatible("J.S.", index) == {"jeffrey skilling", "jonah self"}
    assert compatible("Kay's", index) == {"kay mann"}
    assert compatible("Nobody", index) == set()
    assert compatible("Mark Taylor", index) == {"mark e taylor"}   # initialled keys are indexed by first and last name


def graph(pairs):
    return Distances(pd.DataFrame(pairs, columns=["source", "target"]))


def test_the_candidate_closest_to_both_sender_and_recipient_wins_and_ties_abstain():
    # skilling is one hop from both kay and sara; dasovich is two hops from kay.
    distances = graph([("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"),
                       ("sara shackleton", "jeffrey dasovich"), ("kay mann", "sara shackleton")])
    assert distances.resolve("kay mann", "sara shackleton", {"jeffrey skilling", "jeffrey dasovich"}) == "jeffrey skilling"
    tie = graph([("a b", "c d"), ("a b", "e f"), ("g h", "c d"), ("g h", "e f")])
    assert tie.resolve("a b", "g h", {"c d", "e f"}) is None
    assert distances.resolve("kay mann", "nobody", {"jeffrey skilling"}) is None


def test_links_and_centrality_count_distinct_people_mentioned_to_a_recipient():
    distances = graph([("kay mann", "jeffrey skilling"), ("sara shackleton", "jeffrey skilling"),
                       ("kay mann", "sara shackleton"), ("sara shackleton", "jonah self"), ("kay mann", "jonah self")])
    messages = pd.DataFrame({
        "path": ["m1", "m2"], "sender_person": ["kay mann", "kay mann"],
        "to_people": [["sara shackleton"], ["sara shackleton"]], "cc_people": [[], []],
        "mentions": [["Skilling", "Jonah Self", "Sara"], ["Skilling"]],
    })
    links, counts = mention_links(messages, name_index(PEOPLE), distances)
    assert set(links["person"]) == {"jeffrey skilling", "jonah self", "sara shackleton"}
    parties = pd.Series([{"kay mann", "sara shackleton"}] * 2, index=["m1", "m2"])
    measures = mention_centrality(links, parties).set_index("person_key")
    assert measures.loc["sara shackleton", "mentioned_to"] == 2           # the self-mention "Sara" is dropped
    assert measures.loc["sara shackleton", "mention_degree"] == 2
    assert measures.loc["jeffrey skilling", "mention_degree"] == 1
    assert measures.loc["sara shackleton", "third_party_mentioned_to"] == 2
    assert counts["mentions"] == 4


class FakeNLP:
    meta = {"name": "fake", "version": "1"}
    calls = 0

    def pipe(self, texts, batch_size=256):
        for text in texts:
            FakeNLP.calls += 1
            yield type("Doc", (), {"ents": [type("Ent", (), {"text": w, "label_": "PERSON"}) for w in text.split() if w.istitle()]})


def test_tags_are_cached_and_only_changed_text_is_retagged(tmp_path):
    from enron_importance.mentions import cached_mentions
    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1", "m2"], "authored": ["ask Kay", "tell Sara"]})
    assert list(cached_mentions(messages, cache, FakeNLP())) == [["Kay"], ["Sara"]] and FakeNLP.calls == 2
    messages.loc[1, "authored"] = "tell Jeff"
    assert list(cached_mentions(messages, cache, FakeNLP())) == [["Kay"], ["Jeff"]] and FakeNLP.calls == 3


def test_tags_are_saved_chunk_by_chunk(tmp_path):
    from enron_importance.mentions import cached_mentions

    class Crashing(FakeNLP):
        def pipe(self, texts, batch_size=256):
            for text in texts:
                if "Boom" in text:
                    raise RuntimeError("interrupted")
                yield from FakeNLP.pipe(self, [text])

    cache = tmp_path / "tags.parquet"
    messages = pd.DataFrame({"path": ["m1", "m2", "m3"], "authored": ["ask Kay", "tell Sara", "Boom"]})
    try:
        cached_mentions(messages, cache, Crashing(), chunk=1)
    except RuntimeError:
        pass
    assert len(pd.read_parquet(cache)) == 2       # the two chunks before the failure survive
