from queue import Queue


class FakeExecutor:
    def __init__(self):
        self.calls = []
        self._work_queue = Queue()
        self._threads = [object()]

    def submit(self, fn, *args, **kwargs):
        self.calls.append((fn, args, kwargs))


class DummyController:
    def handle_command(self, command):
        return command

    def handle_event(self, event):
        return event

    def handle_mention(self, event):
        return event


def test_health_endpoint_returns_ok(app):
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.text == "OK"


def test_slack_command_rejects_invalid_token(app):
    client = app.test_client()

    response = client.post(
        "/slack_events/v1/karmabot-v1_commands",
        data={"token": "wrong-token", "command": "/karma", "text": ""},
    )

    assert response.status_code == 403


def test_slack_command_dispatches_karma_only(app, monkeypatch):
    import karmabot.blueprint as blueprint

    fake_executor = FakeExecutor()
    monkeypatch.setattr(blueprint, "executor", fake_executor)
    monkeypatch.setattr(blueprint, "get_karma_controller", lambda: DummyController())
    client = app.test_client()

    response = client.post(
        "/slack_events/v1/karmabot-v1_commands",
        data={
            "token": "test-token",
            "command": "/karma",
            "text": "show shipit",
            "team_id": "T1",
            "user_id": "U1",
        },
    )

    assert response.status_code == 200
    assert len(fake_executor.calls) == 1
    submitted_command = fake_executor.calls[0][1][0]
    assert submitted_command["command"] == "/karma"
    assert submitted_command["text"] == "show shipit"


def test_badge_command_is_ignored(app, monkeypatch):
    import karmabot.blueprint as blueprint

    fake_executor = FakeExecutor()
    monkeypatch.setattr(blueprint, "executor", fake_executor)
    monkeypatch.setattr(blueprint, "get_karma_controller", lambda: DummyController())
    client = app.test_client()

    response = client.post(
        "/slack_events/v1/karmabot-v1_commands",
        data={
            "token": "test-token",
            "command": "/badge",
            "text": "list",
            "team_id": "T1",
            "user_id": "U1",
        },
    )

    assert response.status_code == 200
    assert fake_executor.calls == []


def test_message_event_with_karma_is_dispatched(app, monkeypatch):
    import karmabot.blueprint as blueprint

    fake_executor = FakeExecutor()
    monkeypatch.setattr(blueprint, "executor", fake_executor)
    monkeypatch.setattr(blueprint, "get_karma_controller", lambda: DummyController())
    client = app.test_client()

    response = client.post(
        "/slack_events/v1/karmabot-v1_events",
        json={
            "token": "test-token",
            "team_id": "T1",
            "event": {
                "type": "message",
                "text": "shipit++",
                "user": "U1",
                "channel": "C1",
            },
        },
    )

    assert response.status_code == 200
    assert response.json == {}
    assert len(fake_executor.calls) == 1
    submitted_event = fake_executor.calls[0][1][0]
    assert submitted_event["event"]["text"] == "shipit++"
