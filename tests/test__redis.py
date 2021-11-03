"""Testing authentication flow of App
"""
from datetime import timedelta
from time import sleep

from .fixtures import API, pytestmark, setup  # noqa


async def test_redis(setup):  # noqa
    rd = setup("rd")

    assert (await rd.ping()) is True

    token = "some-token"

    await rd.invalidate_token(token, ttl=timedelta(seconds=3))

    check = await rd.is_token_invalid(token)

    assert check is True

    sleep(1)

    check = await rd.is_token_invalid(token)

    assert check is True

    sleep(2)

    check_again = await rd.is_token_invalid(token)

    assert check_again is False
