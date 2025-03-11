from services.gpt import GPTService
from services.try_on import VirtualTryOn, generate_image_task
from services.user import UserService
from services.rates import RateService
from services.localization import LocalizationService
from services.bg_tasks import app as celery_app


gpt_service = GPTService()
user_service = UserService()
rate_service = RateService()
tryon_service = VirtualTryOn()
localization_service = LocalizationService()

async def get_gpt_service():
    return GPTService()

async def get_user_service():
    return UserService()

async def get_rate_service():
    return RateService()

async def get_tryon_service():
    return VirtualTryOn()

async def get_localization_service():
    return LocalizationService()

