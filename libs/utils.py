from typing import Callable, Optional, Type, TypeVar
from uuid import UUID, uuid1

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


def make_storage_key(image_name: str):
    """Guarantee uniqueness constraint of image_key"""
    storage_key = f"{uuid1()}__{image_name}"
    return storage_key


@trying()
def convert_string_to_uuid(string: str, version=1):
    uuid_obj = UUID(string, version=version)
    return uuid_obj
