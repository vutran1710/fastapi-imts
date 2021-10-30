"""Testing authentication flow of App
"""
import pytest
import pytest_asyncio  # noqa
from fastapi.testclient import TestClient
from main import app
from model.http import AddTagsResponse, AuthResponse
from repository.postgres import Postgres
from settings import settings

client = TestClient(app)

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def setup_pg():
    """Before each test, init a new Postgres instance
    Note that since each test case has its own event-loop,
    the pg instance must be created separately
    """
    pg = await Postgres.init(settings)

    yield pg

    await pg.c.close()


async def test_add_tags(setup_pg):
    """Testing
    - Add tags
    - No need get
    """
    pg = setup_pg

    class API:
        signup = "v1/auth/sign-up"
        login = "v1/auth/login"
        add_tag = "v1/tag"

    email, password = "image-uploader@vutr.io", "123123123"

    # Sign-up with valid credential should succeed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )

    if response.status_code == 400:
        response = client.post(
            API.login,
            data={"username": email, "password": password},
        )

    data = response.json()
    auth = AuthResponse(**data)

    # Add tags
    tags = ["hello", "world"]

    response = client.post(
        API.add_tag,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        json={"tags": tags},
    )

    assert response.status_code == 200
    data = AddTagsResponse(**response.json())
    assert data.tags and len(data.tags) == 2

    for tag in data.tags:
        assert tag in tags

    count = await pg.c.fetchval(
        "SELECT count(*) FROM tags WHERE name IN ('hello', 'world')"
    )
    assert count == 2

    # Add empty tags
    response = client.post(
        API.add_tag,
        headers={"Authorization": f"Bearer {auth.access_token}"},
        json={"tags": ["", "", "---------------"]},
    )

    assert response.status_code == 400

    # cleanup
    await pg.c.fetch("DELETE FROM users WHERE email = $1", email)
    await pg.c.executemany("DELETE FROM tags WHERE name = $1", [("hello",), ("world",)])
