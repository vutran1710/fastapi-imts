from tempfile import SpooledTemporaryFile, TemporaryFile

from logzero import logger as log
from settings import Settings

from minio import Minio as MinioSDK


class Minio:
    def __init__(self, client: MinioSDK, bucket: str):
        self._c = client
        self._bucket = bucket

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

        return cls(client, st.STORAGE_BUCKET)

    def save_image(self, filename: str, file: SpooledTemporaryFile) -> str:
        _, extension = filename.split(".")
        content_type = f"image/{extension}"
        result = self._c.put_object(
            self._bucket,
            filename,
            file,
            -1,
            content_type=content_type,
            part_size=5242880,
        )
        return result.object_name
