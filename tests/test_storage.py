import datetime

from karmabot.storage import KarmaStore


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def test_store_aggregates_karma_by_workspace_type_and_subject(tmp_path):
    store = KarmaStore(tmp_path / "karma.sqlite")
    now = utcnow()
    expires = now + datetime.timedelta(days=1)

    store.store_karma("T1", "thing", "shipit", 1, "U1", now, expires)
    store.store_karma("T1", "thing", "shipit", 2, "U2", now, expires)
    store.store_karma("T1", "user", "U3", -1, "U1", now, expires)
    store.store_karma("T2", "thing", "shipit", 10, "U9", now, expires)

    assert store.get_karma("T1", "thing", "shipit") == 3
    assert store.get_karma("T1", "user", "U3") == -1
    assert store.get_karma("T2", "thing", "shipit") == 10
    assert store.get_all_karma("T1") == 2
    assert store.get_type_karma("T1", "thing") == 3
    assert store.count_karma_operations("T1") == 3
    assert store.count_karma_operations("T1", "thing", "shipit") == 2
    assert store.get_karma_gifter_count("T1") == 2
    assert store.get_subject_count("T1") == 2


def test_store_top_karma_and_gifters(tmp_path):
    store = KarmaStore(tmp_path / "karma.sqlite")
    now = utcnow()
    expires = now + datetime.timedelta(days=1)

    store.store_karma("T1", "thing", "shipit", 1, "U1", now, expires)
    store.store_karma("T1", "thing", "shipit", 3, "U2", now, expires)
    store.store_karma("T1", "thing", "docs", -2, "U1", now, expires)

    assert store.get_top_karma("T1", subject_type="thing", direction=-1, limit=2) == [
        {"subject_type": "thing", "subject": "shipit", "total": 4},
        {"subject_type": "thing", "subject": "docs", "total": -2},
    ]
    assert store.get_top_karma("T1", subject_type="thing", direction=1, limit=1) == [
        {"subject_type": "thing", "subject": "docs", "total": -2},
    ]
    assert store.get_gifters("T1", "thing", "shipit") == [("U2", 3), ("U1", 1)]


def test_expired_karma_is_cleaned_up(tmp_path):
    store = KarmaStore(tmp_path / "karma.sqlite")
    now = utcnow()

    store.store_karma(
        "T1",
        "thing",
        "shipit",
        5,
        "U1",
        now - datetime.timedelta(days=2),
        now - datetime.timedelta(days=1),
    )
    store.store_karma(
        "T1",
        "thing",
        "shipit",
        2,
        "U2",
        now,
        now + datetime.timedelta(days=1),
    )

    assert store.get_karma("T1", "thing", "shipit") == 2
    assert store.count_karma_operations("T1") == 1
