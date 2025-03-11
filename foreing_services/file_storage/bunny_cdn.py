from datetime import datetime
from io import BytesIO
from typing import List

import aiohttp
from config import settings
from fastapi import UploadFile
from foreing_services.file_storage.repository import FileStorage
import asyncio


class BunnyCDN(FileStorage):

    def __init__(self, storage_zone=settings.bunny_cdn.storage_zone, storage_zone_region='de'):
        self.headers = {
            'AccessKey': settings.bunny_cdn.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        self.host_cdn = settings.bunny_cdn.host_cdn  # For GET
        self.base_url = 'https://storage.bunnycdn.com' + storage_zone
        self.now = datetime.now().strftime("%Y%m%d%H%M%S")

    def __construct_url(self, cdn_path: str):
        request_url = self.host_cdn + cdn_path
        return request_url

    async def __upload_file_get_url(self, session: aiohttp.ClientSession,
                                    request_url: str, file, cdn_path: str) -> str:
        print(f'{request_url=}')
        async with session.put(url=request_url, data=file, headers=self.headers) as response:
            return self.__construct_url(cdn_path)

    async def upload_file_get_url(self, file: bytes, folder: str, filename: str, format: str = "jpg") -> str:
        cdn_path = folder + self.now + filename + "." + format
        request_url = self.base_url + cdn_path

        async with aiohttp.ClientSession() as session:
            return await self.__upload_file_get_url(
                session, request_url, file, cdn_path
            )

    async def upload_file_by_url_get_url(self, image_url: str, folder: str) -> str:
        filename = image_url.split("?")[0].split("/")[-1]
        cdn_path = folder + self.now + filename
        request_url = self.base_url + cdn_path

        async with aiohttp.ClientSession() as session:
            async with session.get(url=image_url) as response_image:
                image_content = await response_image.read()
                image_bytes = BytesIO(image_content).getvalue()

            return await self.__upload_file_get_url(session, request_url,
                                             file=image_bytes, cdn_path=cdn_path)

