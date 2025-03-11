from typing import List

from pydantic import BaseModel, Field


class Model(BaseModel):
    id: int
    model: str
    name: str = Field(alias="name_id")
    action: str

    class Config:
        from_attributes = True


class ModelGroup(BaseModel):
    id: int
    rate_id: int
    requests_limit: int

    models: List[Model]

    class Config:
        from_attributes = True


class RateShortSchema(BaseModel):
    id: int
    name: str = Field(alias="name_id")
    is_mine: bool

    class Config:
        from_attributes = True


class RateSchema(RateShortSchema):
    description: str = Field(alias="description_id")
    price_rub: int
    price_usd: int
    price_uzs: int
    price_stars: int
    model_groups: List[ModelGroup]