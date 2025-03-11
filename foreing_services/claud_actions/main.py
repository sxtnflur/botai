import anthropic
from config import  ANTHROPIC_API_KEY
from db.crud import get_localization_text
from foreing_services.gpt_actions.main import get_gpt_action
from db.sql_models.models import GptAction


class AnthropicAPI:
    API_KEY = ANTHROPIC_API_KEY

    def __init__(self, gpt_action: GptAction,
                 key=None, model=None, system_prompt=None, max_tokens=None):
        self.client = anthropic.Anthropic(api_key=self.API_KEY)

        if key:
            self.key = key
        else:
            self.key = gpt_action.key

        if model:
            self.model = model
        else:
            self.model = gpt_action.model_id

        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = gpt_action.system_prompt

        if max_tokens:
            self.max_tokens = max_tokens
        else:
            self.max_tokens = gpt_action.max_tokens

    async def update_object_key(self, key: str, telegram_id: int):
        gpt_action = await self.get_gpt_action(key=key, telegram_id=telegram_id)
        self.key = key
        self.model = gpt_action.model
        self.system_prompt = gpt_action.system_prompt
        self.max_tokens = gpt_action.max_tokens

    @classmethod
    async def get_gpt_action(cls, key: str, telegram_id: int):
        return await get_gpt_action(key, telegram_id, assistant_type="creative_assistant")

    async def check_user_question(self, messages: list, language: str):
        for message in messages:
            print(message)
            if "content" in message and message.get("content")[0].get("type") == "text"\
                    and message.get("role") == "user":
                message_text = message.get("content")[0].get("text").lower()
                print(message_text)
                if "chatgpt" in message_text or\
                        "chat gpt" in message_text:
                    print("THIS TEXT HAS 'chatgpt'!!!")
                    return await get_localization_text(key="ask_chatgpt_answer_text",
                                                       language=language)


    async def send_messages(self, messages: list, language: str, **kwargs):
        check_user_question = await self.check_user_question(messages, language)
        print("check_user_question:", check_user_question)
        if check_user_question:
            return check_user_question

        print("MODEL:", self.model)
        print("MESSAGES:", messages)

        message = self.client.messages.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            system=self.system_prompt,
            **kwargs
        )
        content = message.content
        return content[0].text

    async def send_text_prompt(self, prompt: str, language: str):
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        return await self.send_messages(messages, language)

    async def send_image_prompt(self, image_b64: str, language: str, prompt: str = None):
        content = []
        if prompt:
            content.append({
                    "type": "text",
                    "text": prompt
                })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_b64
            }
        })

        messages = [{
            "role": "user",
            "content": content
        }]
        return await self.send_messages(messages,language)

    async def send_many_photo_urls(self, photo_images_b64: list[str], language: str, caption: str = None):
        content = []
        if caption:
            content.append({
                "type": "text",
                "text": caption
            })

        content += [{
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_b64
            }
        } for image_b64 in photo_images_b64]

        print("MESSAGES:", content)
        messages = [{
            "role": "user",
            "content": content
        }]

        return await self.send_messages(messages, language)