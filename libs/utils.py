from re import findall
from typing import Callable, List, Optional, Type, TypeVar, Union
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


def validate_tag(tag: str) -> bool:
    if len(tag) > 20 or len(tag) < 2:
        return False

    general_pattern = "^([a-zA-Z0-9-]+)$"
    invalid_pattern = "^([0-9-]+)$"

    valid = findall(general_pattern, tag)
    invalid = findall(invalid_pattern, tag)

    return bool(valid and len(valid) == 1 and not invalid)


def fix_tags(tags: Union[List[str], str, None]) -> List[str]:
    """extract only valid tags, remove duplicate as well"""
    if not tags:
        return []

    tag_list = tags.split(",") if isinstance(tags, str) else tags
    valid_tags_only = [t.lower().strip() for t in tag_list if validate_tag(t)]
    return list(set(valid_tags_only))
