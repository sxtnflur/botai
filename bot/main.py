import asyncio
from contextlib import asynccontextmanager

from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from fastapi import FastAPI, Request, BackgroundTasks

from aiogram import Bot, Dispatcher, types
from aiogram.types import Update
from config import settings as config_settings, ADMIN_IDS
from bot.handlers import __routers__
from bot.middleware import AuthMiddleware


bot = Bot(token=config_settings.api.TELEGRAM_BOT)
dp = Dispatcher(storage=RedisStorage(
    redis=Redis.from_url(config_settings.redis.create_url(db=2))
))

dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())


@asynccontextmanager
async def lifespan(app: FastAPI):
    url_webhook = f"https://{config_settings.domain}/tg_bot_webhook"

    await bot.session.close()

    await bot.set_webhook(
        url=url_webhook,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True, request_timeout=60
    )
    await send_admin_message(bot, "Система обновлена")

    await bot.session.close()

    dp.include_routers(*__routers__)

    yield

    await send_admin_message(bot, "Система на обновлении")
    await bot.delete_webhook()

    await bot.session.close()
    await bot.close()

async def send_admin_message(bot: Bot, text: str):
    for admin_id in ADMIN_IDS:
        await bot.send_message(chat_id=admin_id, text=text)

async def main():
    try:
        await bot.set_my_commands(
            [
                types.BotCommand(command="start", description="Запуск бота")
            ],
            types.BotCommandScopeDefault()
        )
    except:
        pass

    dp.include_routers(*__routers__)

    while True:
        try:
            await dp.start_polling(bot, close_bot_session=True, polling_timeout=30)
        except Exception as e:
            print(e)
            continue


app = FastAPI(lifespan=lifespan)

async def feed_update(update: Update):
    await dp.feed_update(bot, update)

@app.post("/tg_bot_webhook")
async def webhook(request: Request, bg_tasks: BackgroundTasks) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    bg_tasks.add_task(feed_update, update)
    # await dp.feed_update(bot, update)


if __name__ == '__main__':
    asyncio.run(main())
