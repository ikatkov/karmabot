import time

from karmabot.controller.karma import KarmaController


def message_event(text, user="U1"):
    return {
        "token": "test-token",
        "team_id": "T1",
        "rec_time": time.time(),
        "event": {
            "type": "message",
            "text": text,
            "user": user,
            "channel": "C1",
        },
    }


def command(text, user="U1"):
    return {
        "token": "test-token",
        "team_id": "T1",
        "user_id": user,
        "channel_id": "C1",
        "command": "/karma",
        "text": text,
        "response_url": "https://slack.example/response",
    }


def test_message_event_stores_karma_for_supported_subjects(app_context, monkeypatch):
    posts = []
    errors = []

    monkeypatch.setattr(
        "karmabot.service.slack.get_userinfo",
        lambda workspace, user_id: {"ok": True, "user": {"id": user_id, "is_bot": False}},
    )
    monkeypatch.setattr("karmabot.service.slack.post_attachment", lambda workspace, post: posts.append(post))
    monkeypatch.setattr(
        "karmabot.service.slack.post_message",
        lambda workspace, channel, text, parse="full", thread_ts=None: errors.append(text),
    )

    controller = KarmaController()
    controller.handle_event(message_event('shipit++ <@U2>-- "quoted thing"++ shipit++'))

    assert controller.get_karma("T1", "thing", "shipit") == 1
    assert controller.get_karma("T1", "user", "U2") == -1
    assert controller.get_karma("T1", "thing", "quoted thing") == 1
    assert controller.store.count_karma_operations("T1") == 3
    assert errors == []
    assert len(posts) == 3


def test_message_event_rejects_self_karma(app_context, monkeypatch):
    errors = []
    posts = []

    monkeypatch.setattr(
        "karmabot.service.slack.get_userinfo",
        lambda workspace, user_id: {"ok": True, "user": {"id": user_id, "is_bot": False}},
    )
    monkeypatch.setattr(
        "karmabot.service.slack.post_message",
        lambda workspace, channel, text, parse="full", thread_ts=None: errors.append(text),
    )
    monkeypatch.setattr("karmabot.service.slack.post_attachment", lambda workspace, post: posts.append(post))

    controller = KarmaController()
    controller.handle_event(message_event("<@U1>++", user="U1"))

    assert errors == ["Don't be so vain"]
    assert posts == []
    assert controller.get_karma("T1", "user", "U1") == 0


def test_show_command_responds_with_current_karma(app_context, monkeypatch):
    responses = []
    controller = KarmaController()
    controller.store_karma("thing", "shipit", 3, "U2", "T1")

    monkeypatch.setattr(
        "karmabot.service.slack.command_reply",
        lambda workspace, url, message: responses.append(message),
    )

    controller.handle_command(command("show shipit"))

    assert len(responses) == 1
    attachment = responses[0]["attachments"][0]
    assert attachment["text"] == "shipit has 3 karma. (Thing) "


def test_top_command_includes_highest_karma_subject(app_context, monkeypatch):
    responses = []
    controller = KarmaController()
    controller.store_karma("thing", "shipit", 3, "U2", "T1")
    controller.store_karma("thing", "docs", 1, "U3", "T1")

    monkeypatch.setattr(
        "karmabot.service.slack.command_reply",
        lambda workspace, url, message: responses.append(message),
    )

    controller.handle_command(command("top things"))

    field = responses[0]["attachments"][0]["fields"][0]
    assert field["title"] == "Top Thing Karma Standings"
    assert "3  shipit (thing)" in field["value"]
    assert "1  docs (thing)" in field["value"]
