from enum import Enum

from config import settings
from .base import FalBase
from .schemas import ResultFashn


class FalKlingTryOn(FalBase):
    url = "fal-ai/kling/v1-5/kolors-virtual-try-on"


class FashCategory(str, Enum):
    tops = "tops"
    bottoms = "bottoms"
    one_pieces = "one-pieces"


class GarmentPhotoTypeEnum(str, Enum):
    auto = "auto"
    model = "model"
    flat_lay = "flat-lay"


class FalFashnTryOn(FalBase[ResultFashn]):
    url = "fashn/tryon"
    base_callback_url = f"{settings.stylist_api_url}/try_on/result/bot/fashn"
    result_schema = ResultFashn

    async def generate_subscribed(self, human_image: str, cloth_image: str, callback_url: str = base_callback_url,
                       **kwargs) -> ResultFashn:
        category: FashCategory | None = None
        if "category" in kwargs:
            category = kwargs.get("category")

        return await super(FalFashnTryOn, self).generate_subscribed(
            **{
                "model_image": human_image,
                "garment_image": cloth_image,
                "category": category,
                "adjust_hands": True,  # Разрешить изменять руки
                "restore_background": True,  # Сохранить фон
                "restore_clothes": True,  # Сохранить неизменяемую одежду
                "cover_feet": True,  # Позволяет длинной одежде закрывать ноги / обувь или изменять их внешний вид
                "garment_photo_type": GarmentPhotoTypeEnum.auto,  # Тип фото одежды (на человеке/без человека/авто)
                "timesteps": 50,  # Увеличить для повышения качества / Уменьшить для ускорения (Макс: 50)
                "output_format": "png"
            }
        )

    async def generate(self, human_image: str, cloth_image: str, callback_url: str = base_callback_url,
                       **kwargs) -> str:
        category: FashCategory | None = None
        if "category" in kwargs:
            category = kwargs.get("category")

        return await super(FalFashnTryOn, self).generate(
            **{
                "model_image": human_image,
                "garment_image": cloth_image,
                "category": category,
                "adjust_hands": True,  # Разрешить изменять руки
                "restore_background": True,  # Сохранить фон
                "restore_clothes": True,  # Сохранить неизменяемую одежду
                "cover_feet": True,  # Позволяет длинной одежде закрывать ноги / обувь или изменять их внешний вид
                "garment_photo_type": GarmentPhotoTypeEnum.auto,  # Тип фото одежды (на человеке/без человека/авто)
                "timesteps": 50,  # Увеличить для повышения качества / Уменьшить для ускорения (Макс: 50)
                "output_format": "png"
            }
        )