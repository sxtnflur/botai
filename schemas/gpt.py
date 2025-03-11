from pydantic import BaseModel, Field
from enum import Enum

class UserMinusRequest(BaseModel):
    has_tokens: bool
    available_model: str | None = None

class GPTResponseStatus(str, Enum):
    succeed = "succeed"
    not_enough_tokens = "not_enough_tokens"

class TextResponse(BaseModel):
    status: GPTResponseStatus
    answer_text: str | None = None
    thread_id: str | None = None
    chat_name: str | None = None
    created_db_thread_id: int | None = None

class ImageResponse(BaseModel):
    status: GPTResponseStatus
    image_url: str | None = None



class GPTAssistantSchema(BaseModel):
    id: int
    assistant_id: str
    action_name: str
    action_description: str | None = Field(default='')

    name: str | None = None
    description: str | None = None
    instructions: str | None = None

    class Config:
        from_attributes = True


class AssistantData(BaseModel):
    assistant_id: str
    model: str
    max_tokens: int


class WardrobeElementResponse(BaseModel):
    id: int
    image_url: str
    gpt_file_id: str
    name: str

    class Config:
        from_attributes = True


class WardrobeElementDeleted(BaseModel):
    gpt_file_id: str


class FilePurpose(str, Enum):
    assistants = "assistants"
    vision = "vision"
    fine_tune = "fine-tune"
    batch = "batch"
    user_data = "user-data"
    evals = "evals"