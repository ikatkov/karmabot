import pytest

from karmabot import create_app
from karmabot import storage


@pytest.fixture(autouse=True)
def reset_store():
    storage._store = None
    yield
    storage._store = None


@pytest.fixture
def app(tmp_path):
    app = create_app()
    app.config.update(
        TESTING=True,
        FAKE_SLACK=True,
        VERIFICATION_TOKEN="test-token",
        SQLITE_PATH=str(tmp_path / "karmabot.sqlite"),
    )
    return app


@pytest.fixture
def app_context(app):
    with app.app_context():
        yield app
