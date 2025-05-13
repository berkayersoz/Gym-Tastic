import sqlite3
import pytest
import db as db_module
from main import app as flask_app

@pytest.fixture(scope='session')
def test_db_path(tmp_path_factory):
    # one SQLite file for the session
    db_file = tmp_path_factory.mktemp("data") / "fitness_test.db"
    # initialize tables + default exercises once
    db_module.initialize_database(str(db_file))
    return str(db_file)

@pytest.fixture(autouse=True)
def reset_db_between_tests(monkeypatch, test_db_path):
    """
    Monkeypatch sqlite3.connect to always use our test_db_path,
    then BEFORE each test wipe & re‐seed it, and AFTER each test wipe it again.
    """
    # patch all sqlite3.connect calls to use our single file
    orig = sqlite3.connect
    def connect_override(path, *args, **kwargs):
        return orig(test_db_path, *args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', connect_override)

    # before test: clear everything & re‐insert default exercises
    db_module.reset_database(test_db_path)
    db_module.initialize_database(test_db_path)

    yield

    # after test: clear it so no data leaks into the next test
    db_module.reset_database(test_db_path)

@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c
