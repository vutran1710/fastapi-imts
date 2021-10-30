"""Unit testing utility functions
"""
from datetime import datetime

import pytest  # noqa
import pytest_asyncio  # noqa
from fastapi import HTTPException
from libs.exceptions import AuthException
from libs.utils import (initialize_model, raise_if_falsy, trying,
                        validate_image_file)
from pydantic import BaseModel


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


def test_raise_on_falsy():
    """A short function that help raise HTTPException on having Falsy/None value returned"""
    try:
        raise_if_falsy(ValueError, None)
        assert False
    except ValueError:
        pass

    try:
        raise_if_falsy(AuthException.DUPLICATE_USER, False)
        assert False
    except HTTPException as e:
        assert e == AuthException.DUPLICATE_USER


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
