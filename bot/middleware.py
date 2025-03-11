from aiogram import BaseMiddleware
from typing import Union, Dict, Any, Callable, Awaitable

from aiogram.dispatcher.flags import extract_flags
from aiogram.types import Message, TelegramObject, User
import asyncio
from services import user_service


class AlbumMiddleware(BaseMiddleware):
    """This middleware is for capturing media groups."""

    album_data: dict = {}

    def __init__(self, latency: Union[int, float] = 0.5):
        """
        You can provide custom latency to make sure
        albums are handled properly in highload.
        """
        self.latency = latency
        super().__init__()

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]):

        if isinstance(event, Message):
            message = event
        else:
            return await handler(event, data)
        print(f'{message.media_group_id=}')

        if not message.media_group_id:
            data["album"] = None
            return await handler(event, data)

        print(f'{self.album_data=}')
        try:
            self.album_data[message.media_group_id].append(message)
            return
            # raise CancelHandler()  # Tell aiogram to cancel handler for this group element
        except KeyError:
            self.album_data[message.media_group_id] = [message]
            await asyncio.sleep(self.latency)
            message.model_config["is_last"] = True
            data["album"] = self.album_data[message.media_group_id]

            result = await handler(event, data)

            if message.media_group_id and message.model_config.get("is_last"):
                del self.album_data[message.media_group_id]

            return result



class AuthMiddleware(BaseMiddleware):
    def __init__(self):
        super(AuthMiddleware, self).__init__()

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]):
        try:
            flags = extract_flags(data)
            if flags.get("auth_off"):
                return await handler(event, data)

            if event.bot.id == event.from_user.id:
                return await handler(event, data)
            tg_user: User = event.from_user
            user_reg_data = await user_service.get_user_reg_data(
                telegram_id=tg_user.id,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                username=tg_user.username
            )
            print(f"{user_reg_data=}")
            data["user_data"] = user_reg_data
            return await handler(event, data)
        except Exception as e:
            print("ERROR:", e)
