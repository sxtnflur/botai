import io

import aiohttp
import requests
from PIL import Image
import base64
from io import BytesIO


async def bytes_to_bytesio(file: bytes, filename: str = None):
    buffer = BytesIO(file)
    if filename:
        buffer.name = filename
    return buffer


async def bytes_to_b64(file: bytes):
    return base64.b64encode(file).decode("utf-8")

async def image_url_to_b64(image_url: str):
    async with aiohttp.ClientSession() as sesssion:
        async with sesssion.get(image_url) as response:
            return base64.b64encode(await response.read()).decode("utf-8")

async def image_url_to_bytes(image_url: str) -> bytes:
    async with aiohttp.ClientSession() as sesssion:
        async with sesssion.get(image_url) as response:
            return await response.read()

def file_to_b64(path: str):
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def change_file_format(path: str, new_format: str = "jpg"):
    new_name = path.split(".")[0] + "." + new_format
    Image.open(path).save(new_name, format=new_format)


# def change_file_url_format(url: str, new_format: str):
#     file_bytes = await image_url_to_bytes(image_url=url)
#     file_bytesio = io.BytesIO(file_bytes)
#


def convert_image_url(image_url: str, convert_to: str = "RGB") -> bytes:
    img_bytes = requests.get(image_url).content
    img_bytesio = io.BytesIO(img_bytes)
    img = Image.open(img_bytesio)
    res = img.convert(convert_to)
    return res.tobytes()
