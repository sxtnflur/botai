from datetime import datetime
from enum import Enum

from foreing_services.hugging_face_service.schemas import GeneralGarmentType
from pydantic import BaseModel, Field


class ClothCategorySchema(BaseModel):
    id: int
    name: str = Field(alias="name_id")
    garment_type: GeneralGarmentType

    class Config:
        from_attributes = True


class KlingTokenSchema(BaseModel):
    id: int
    access_key: str
    secret_key: str
    remaining_quantity: int | None
    is_expired: bool | None

    class Config:
        from_attributes = True

class KlingTaskSchema(BaseModel):
    id: int
    user_telegram_id: int
    task_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class TryonPhotoSchema(BaseModel):
    id: int
    cloth_category: ClothCategorySchema | None = None
    created_at: datetime
    task_id: str
    human_image: str

    class Config:
        from_attributes = True

class TryonPhotosResponse(BaseModel):
    result: list[TryonPhotoSchema]
    has_else: bool = True


class GenerateTryOnStatus(str, Enum):
    client_has_not_requests = "client_has_not_requests"
    server_has_not_requests = "server_has_not_requests"
    succeed = "succeed"


class GenerateTryOnResponse(BaseModel):
    status: GenerateTryOnStatus
    human_image: str | None = None
    cloth_image: str | None = None
    task_id: str | None = None
