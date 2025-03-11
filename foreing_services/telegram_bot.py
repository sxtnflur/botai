import json

import aiohttp
from config import settings


class TelegramBotException(Exception):
    ...


class TelegramBotService:

    bot_token = settings.api.TELEGRAM_BOT

    base_url = f"https://api.telegram.org/bot{bot_token}/"

    async def send_text_message(self, chat_id: int, text: str,
                                inline_keyboard: list[list[dict]] | None = None,
                                parse_mode: str = "html"
                                ):
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        if inline_keyboard:
            data.update(reply_markup=json.dumps({
                "inline_keyboard": inline_keyboard
            }))

        url = self.base_url + "sendMessage"
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, json=data) as response:
                status_code = response.status
                res_json = await response.json()

        if status_code >= 400:
            raise TelegramBotException(str(res_json))

    async def send_photo_message(self, chat_id: int, photo: str, caption: str | None = None,
                                 inline_keyboard: list[list[dict]] | None = None,
                                 parse_mode: str = "html"):
        data = {
            "chat_id": chat_id,
            "photo": photo,
            "parse_mode": parse_mode
        }
        print(f'{inline_keyboard=}')

        if caption:
            data.update(caption=caption)

        if inline_keyboard:
            data.update(reply_markup=json.dumps({
                "inline_keyboard": inline_keyboard
            }))
        print(f'{data=}')

        url = self.base_url + "sendPhoto"
        async with aiohttp.ClientSession() as session:
            async with session.post(url=url, data=data) as response:
                status_code = response.status
                res_json = await response.json()

        if status_code >= 400:
            raise TelegramBotException(str(res_json))

