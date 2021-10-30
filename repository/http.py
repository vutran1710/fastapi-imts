from typing import Optional

from httpx import AsyncClient, Response

from model.auth import FBLoginData
from model.http import FBUserInfo


class Http:
    def __init__(self):
        self._c = AsyncClient()

    async def authenticate_facebook_user(
        self, data: FBLoginData
    ) -> Optional[FBUserInfo]:
        url = f"https://graph.facebook.com/v12.0/{data.user_id}/"
        params = {
            "access_token": data.access_token,
            "fields": ",".join(["email", "name", "picture"]),
        }
        resp: Response = await self._c.get(url, params=params)
        await self._c.aclose()

        if resp.status_code != 200:
            return None

        fb_response: dict = resp.json()
        return FBUserInfo(**fb_response)
