from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose.jwt import decode, encode
from logzero import logger as log

from settings import Settings


class Jwt:
    def __init__(self, st: Settings):
        self._k = st.JWT_SECRET

    def encode(self, data: dict, **expire_times) -> Tuple[str, int]:
        now = datetime.now()
        iat = int(now.timestamp())
        exp = int((now + timedelta(**expire_times)).timestamp())
        issuer = "itms"
        data.update({"exp": exp, "iat": iat, "issuer": issuer})
        jwt = encode(data, self._k, algorithm="HS256")
        return jwt, exp

    def decode(self, token: str) -> Optional[dict]:
        try:
            data = decode(
                token,
                self._k,
                options={"verify_signature": True},
            )
            return data
        except Exception as err:
            log.error("Invalid token: %s", err)
            return None
