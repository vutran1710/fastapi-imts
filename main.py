from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api
from settings import settings

app = FastAPI(title="IMT-App")


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_ALLOWED,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api.AuthRouter,
    prefix="/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    api.ImageRouter,
    prefix="/v1/image",
    tags=["Image"],
)

app.include_router(
    api.TagRouter,
    prefix="/v1/tag",
    tags=["Tags"],
)
