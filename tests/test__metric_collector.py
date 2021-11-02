"""Unit testing the custom Postgres module
"""
from datetime import datetime

from logzero import logger as log
from model.auth import AuthenticatedUser
from model.metrics import UserTracking
from repository.metric_collector import Collections

from .fixtures import pytestmark, setup  # noqa


async def test_initialize(setup):  # noqa
    mc = setup[3]
    assert (await mc.healthz()) is True
    user = AuthenticatedUser(
        name="messi",
        user_id=2,
        email="me@vutr.io",
        provider="app",
        token="some-tokken",
        exp=datetime.now(),
    )

    # Test saving simple tracking data
    request_url = "htpp://localhost:8000/image/"
    now = datetime.now().timestamp()
    user_tracking_data = UserTracking(
        **user.dict(), request_url=request_url, timestamp=now
    )

    assert user_tracking_data

    doc_id = await mc.collect_user(user, request_url)
    log.info("Log's id collected = %s", doc_id)
    assert doc_id

    get_log = await mc.db[Collections.TRACKING_USERS].find_one({"_id": doc_id})
    assert get_log
    assert get_log["request_url"] == request_url
    assert get_log["email"] == user.email
    assert get_log["user_id"] == user.user_id
    log.info(get_log)

    # Test saving tracking data with extra data/metadata
    metadata = {"user_level": 3, "client_type": "business", "tags": ["foo", "bar"]}
    doc_id = await mc.collect_user(user, request_url, extra=metadata)
    assert doc_id

    get_log = await mc.db[Collections.TRACKING_USERS].find_one({"_id": doc_id})
    assert get_log
    assert get_log["extra"] == metadata
