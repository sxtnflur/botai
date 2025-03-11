from enum import Enum

from pydantic import BaseModel
from typing_extensions import Generic, TypeVar


#  BASE

SuccessPayloadT = TypeVar("SuccessPayloadT", bound=BaseModel)
ErrorPayloadT = TypeVar("ErrorPayloadT", bound=BaseModel)

class BaseResult(BaseModel, Generic[SuccessPayloadT, ErrorPayloadT]):
    request_id: str
    gateway_request_id: str | None = None
    status: str | None = None
    payload: SuccessPayloadT | ErrorPayloadT


#  ----
class Image(BaseModel):
    height: int | None = None
    width: int | None = None
    content_type: str | None = None
    url: str


class Payload(BaseModel):
    image: Image
    seed: int | None = None
    has_nsfw_concepts: bool | None = None

class PayloadError(BaseModel):
    detail: str


Result = BaseResult[Payload, PayloadError]



# FASHN

class PayloadFashn(BaseModel):
    images: list[Image]


class FashnErrorsEnum(str, Enum):
    ImageLoadError = "ImageLoadError"
    NSFWError = "NSFWError"
    PhotoTypeError = "PhotoTypeError"
    PoseError = "PoseError"
    PipelineError = "PipelineError"


class ErrorFashn(BaseModel):
    type: str
    name: FashnErrorsEnum
    message: str

class PayloadErrorFashn(BaseModel):
    detail: ErrorFashn



ResultFashn = BaseResult[PayloadFashn, PayloadErrorFashn]


# ResultIdeogram = BaseResult[PayloadFashn, PayloadErrorFashn]
class ResultIdeogram(BaseResult[PayloadFashn, PayloadErrorFashn]):
    ...

