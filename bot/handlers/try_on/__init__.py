from bot.handlers.try_on.try_on import router as tryon_router
from bot.handlers.try_on.cloth_models import router as cloth_models_router
from bot.handlers.try_on.use_my_photos import router as use_my_photos_router


__tryon_routers__ = (tryon_router, cloth_models_router, use_my_photos_router)