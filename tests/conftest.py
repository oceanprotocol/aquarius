import pytest

from provider.run import app

app = app


@pytest.fixture
def client():
    client = app.test_client()
    yield client

