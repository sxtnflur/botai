from foreing_services.file_storage.firebase_storage import FirebaseStorage
from foreing_services.file_storage.bunny_cdn import BunnyCDN
from foreing_services.file_storage.repository import FileStorage


async def get_file_storage_service():
    return BunnyCDN()