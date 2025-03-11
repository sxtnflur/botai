from io import BytesIO
from pathlib import Path
from PIL import Image
from aiogram import Bot
import base64
from aiogram.types import Voice, Message
from config import BASE_DIR
from config import settings
import httpx

async def tg_image_to_b64(file_id: str, bot: Bot) -> base64:
    photo = await bot.get_file(file_id=file_id)
    return base64.standard_b64encode(httpx.get(
        f'https://api.telegram.org/file/bot{settings.api.TELEGRAM_BOT}/' + photo.file_path
    ).content).decode("utf-8")


async def tg_photo_to_url(message: Message):
    if not message.photo:
        raise Exception("В сообщении нет фото")

    photo = message.photo[-1]

    photo = photo.file_id
    photo = await message.bot.get_file(file_id=photo)
    return f'https://api.telegram.org/file/bot{settings.api.TELEGRAM_BOT}/' + photo.file_path


async def tg_photo_to_b64(message: Message):
    url = await tg_photo_to_url(message=message)

    return base64.standard_b64encode(httpx.get(url).content).decode("utf-8")

async def tg_photo_to_bytes(file_id: str, bot: Bot) -> bytes:
    photo = await bot.get_file(file_id=file_id)
    return (await bot.download_file(file_path=photo.file_path)).read()
    # return BytesIO(httpx.get(
    #     f'https://api.telegram.org/file/bot{settings.api.TELEGRAM_BOT}/' + photo.file_path
    # ).content).getvalue()

async def save_voice_as_mp3(voice: Voice) -> str:
    """Скачивает голосовое сообщение и сохраняет в формате mp3."""
    voice_mp3_path = f"{BASE_DIR}/files/voice-{voice.file_unique_id}.mp3"

    voice_file_info = await voice.bot.get_file(voice.file_id)
    # voice_ogg = io.BytesIO()
    await voice.bot.download_file(file_path=voice_file_info.file_path, destination=Path(voice_mp3_path))
    # AudioSegment.from_file(voice_mp3_path, format="ogg").export(
    #     voice_mp3_path, format="mp3"
    # )
    return voice_mp3_path


def file_to_b64(path: str):
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
    return encoded_string


def change_file_format(path: str, new_format: str = "jpg"):
    new_name = path.split(".")[0] + "." + new_format
    print(f"{new_name=}")
    Image.open(path).save(new_name, format=new_format)


async def download_telegram_photo(bot: Bot, file_id: str, destination: Path):
    file = await bot.get_file(file_id=file_id)
    await bot.download_file(file_path=file.file_path, destination=destination)



