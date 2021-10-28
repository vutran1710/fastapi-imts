from typing import Any, Callable, Optional, Type, TypeVar
from uuid import uuid1

from google.auth.transport import requests
from google.oauth2 import id_token
from settings import settings

T = TypeVar("T")


def trying(on_exception=None):
    """A decorator to reduce the boilerplate of try-except"""

    def wrapped_(f: Callable):
        def wrapped(*args, **kwrags):
            try:
                return f(*args, **kwrags)
            except Exception:
                return on_exception

        return wrapped

    return wrapped_


def raise_if_falsy(exception: Exception, value: Any):
    if not value:
        raise exception

    return value


@trying()
def initialize_model(model: Type[T], **kwargs) -> Optional[T]:
    """Trying to intialize a pydantic-model instance
    Return None on failure instead of raising error
    """
    return model(**kwargs)  # type: ignore


@trying(False)
def validate_google_user(idtoken: str, email: str) -> bool:
    """Validate if User are using valid GoogleAccount to sign-up/login"""
    idinfo = id_token.verify_oauth2_token(
        idtoken,
        requests.Request(),
        settings.GOOGLE_APP_CLIENT_ID,
    )
    return idinfo.get("email") == email


@trying(False)
def validate_image_file(filename: str):
    """Only accept file name for images of type PNG / JPG / JPEG"""
    name, ext = filename.lower().split(".")
    valid_extensions = ("png", "jpg", "jpeg")
    return name and ext in valid_extensions


def fix_image_name(filename: str):
    """Guarantee uniqueness constraint of image_key"""
    new_name = f"{uuid1()}__{filename}"
    return new_name
