from typing import List

from fastapi import UploadFile
from firebase_admin import storage
from foreing_services.file_storage.repository import FileStorage
import base64
from time import time


class FirebaseStorage(FileStorage):
    async def upload_file_get_url(self, file: base64, folder: str, filename: str, format: str = "jpg") -> str:

        if folder.endswith("/"):
            file_path = folder + str(round(time())) + filename + "." + format
        else:
            file_path = folder + "/" + str(round(time())) + filename + "." + format

        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        blob.upload_from_string(file, content_type=f"image/{format}")
        blob.make_public()
        return blob.public_url

    async def delete_file(self, file_url: str):
        bucket = storage.bucket()
        blob = bucket.blob(file_url.split('/')[-1])
        blob.delete()