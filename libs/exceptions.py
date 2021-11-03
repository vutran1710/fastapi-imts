from fastapi import HTTPException


class AuthException:
    INVALID_EMAIL_PWD = HTTPException(400, "Invalid email or password")
    INVALID_CREDENTIAL = HTTPException(400, "Invalid user credential format")
    DUPLICATE_USER = HTTPException(400, "User already exists")
    INVALID_SOCIAL_TOKEN = HTTPException(400, "User's social token is invalid")

    FAIL_GOOGLE_AUTH = HTTPException(400)
    FAIL_FACEBOOK_AUTH = HTTPException(400)


class ImageException:
    IMAGE_ONLY = HTTPException(400, "Only images allowed")
    IMAGE_NOT_FOUND = HTTPException(404, "Image not found")


class TagException:
    INVALID_TAGS = HTTPException(400, "Invalid tags")
