"""Unit testing utility functions
"""
from uuid import uuid1, uuid4

import pytest  # noqa
import pytest_asyncio  # noqa
from pydantic import BaseModel

from libs.utils import (convert_string_to_uuid, initialize_model, trying,
                        validate_image_file)


def test_trying_decorator():
    @trying()
    def will_raise():
        """Default return is None if raised"""
        raise Exception

    assert will_raise() is None

    @trying(on_exception=1)
    def will_raise():
        """Default return is 1 if raised"""
        raise Exception

    assert will_raise() == 1

    @trying(False)
    def will_raise():
        """Default return is False if raised"""
        raise Exception

    assert will_raise() is False


def test_initializing_model():
    """Make Pydantic model initialization fault-tolerant"""

    class SampleModel(BaseModel):
        some_val: int

    model_instance = initialize_model(SampleModel, some_val="invalid")
    assert model_instance is None

    model_instance = initialize_model(SampleModel, no_val=None)
    assert model_instance is None

    model_instance = initialize_model(SampleModel, some_val=1)
    assert isinstance(model_instance, SampleModel)


def test_validate_image():
    valid_names = [
        "abcb.jpg",
        "ABCB.JPG",
        "asd-sadfsad-sdf.PNG",
        "asd-sadfsad-sdf.png",
        "ASD-sadfsad-sdf.jpeg",
    ]

    for n in valid_names:
        assert validate_image_file(n) is True

    invalid_names = [
        "asdfadf",
        "adddfs.mov",
        "sadfasdmov",
        "sadfasdjpg",
    ]

    for n in invalid_names:
        assert validate_image_file(n) is False


def test_string_uuid_conversion():
    valid_id = uuid1()
    str_uuid = str(valid_id)
    uuid_convert = convert_string_to_uuid(str_uuid)

    assert str(uuid_convert) == str_uuid

    invalid = convert_string_to_uuid("sdfsdf")
    assert invalid is None

    valid_id = uuid4()
    str_uuid = str(valid_id)
    uuid_convert = convert_string_to_uuid(str_uuid, version=4)

    assert str(uuid_convert) == str_uuid

    invalid = convert_string_to_uuid("sdfsdf", version=4)
    assert invalid is None
