from logzero import logger as log
from minio import Minio as MinioSDK

from settings import Settings


class Minio:
    def __init__(self, client):
        self._c = client

    @classmethod
    def init(cls, st: Settings):
        client = MinioSDK(
            st.STORAGE_HOST,
            access_key=st.STORAGE_ACCESS_KEY,
            secret_key=st.STORAGE_SECRET_KEY,
            secure=st.is_prod,
        )
        found_bucket = client.bucket_exists(st.STORAGE_BUCKET)

        if not found_bucket:
            client.make_bucket(st.STORAGE_BUCKET)
            log.info(
                "Creating bucket %s",
                st.STORAGE_BUCKET,
            )
        else:
            log.info(
                "Bucket %s already exists",
                st.STORAGE_BUCKET,
            )

        return cls(client)
