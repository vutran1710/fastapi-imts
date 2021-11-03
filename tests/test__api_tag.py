"""Testing authentication flow of App
"""
from model.http import AddTagsResponse, AuthResponse

from .fixtures import API, pytestmark, setup  # noqa


async def test_add_tags(setup):  # noqa
    """Testing
    - Add tags
    - No need get
    """
    client, pg = setup("app", "pg")

    email, password = "image-uploader@vutr.io", "123123123"

    # Sign-up with valid credential should succeed
    response = client.post(
        API.signup,
        data={"username": email, "password": password},
    )

    data = response.json()
    auth = AuthResponse(**data)
    headers = {"Authorization": f"Bearer {auth.access_token}"}

    # Add tags
    tags = ["hello", "world"]
    response = client.post(API.add_tag, headers=headers, json={"tags": tags})

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
    invalid_tags = ["", "", "--", "#-"]
    response = client.post(API.add_tag, headers=headers, json={"tags": invalid_tags})
    assert response.status_code == 400
