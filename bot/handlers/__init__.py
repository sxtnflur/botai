from bot.handlers.start import router as start_router
from bot.handlers.gpt import router as gpt_router
from bot.handlers.anthropic import router as anthropic_router
from bot.handlers.rates import router as rates_router
from bot.handlers.settings import router as settings_router
from bot.handlers.threads import router as threads_router
from bot.handlers.try_on import __tryon_routers__
from bot.handlers.admin import router as admin_router
from bot.handlers.wardrobe import router as wardrobe_router


__routers__ = (
    start_router, gpt_router, rates_router, settings_router,
    threads_router, *__tryon_routers__, wardrobe_router, admin_router
)