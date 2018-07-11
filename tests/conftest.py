import pytest

from provider_backend.run import app

app = app


@pytest.fixture
def client():
    client = app.test_client()
    yield client

