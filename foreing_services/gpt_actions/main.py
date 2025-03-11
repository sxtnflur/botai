import os

from db.crud import get_localization_text
from db.database import connection
from openai import OpenAI
from config import OPENAI_KEY
from db.sql_models.models import GptAction
from sqlalchemy import text


@connection
async def get_gpt_action(session, key: str, telegram_id: int, assistant_type: str):
    stmt = """
        SELECT ga.key, ga.system_prompt, am.model_id, rates.max_tokens, am.id
        FROM gpt_actions ga
        
        JOIN users ON users.telegram_id = :telegram_id
        LEFT JOIN users_tokens_models utm ON utm.user_id = users.id
        LEFT JOIN rates_ai_models ram ON ram.rate_id = users.rate_id
        LEFT JOIN rates ON rates.id = users.rate_id
        
        JOIN ai_models my_am ON (
        my_am.id = utm.model_id OR my_am.id= ram.model_id
        ) AND my_am.assistant_type = :assistant_type
        JOIN actions_ai_models aam ON aam.action_key = ga.key
        JOIN ai_models am ON ((am.id = aam.model_id AND am.assistant_type = :assistant_type
        AND (am.id = utm.model_id OR am.id = ram.model_id)) OR
        am.id = my_am.child_model_id AND am.id = aam.model_id)
        
        WHERE ga.key = :key
    """
    result = await session.execute(text(stmt), dict(
        telegram_id=telegram_id,
        key=key,
        assistant_type=assistant_type
    ))
    gpt_action = result.first()
    return gpt_action



class ChatGPT4:
    API_KEY = OPENAI_KEY
    key = "text"
    telegram_id = None

    def __init__(self, gpt_action: GptAction,
                 key=None, model=None, system_prompt=None, max_tokens=None):
        self.client = OpenAI(api_key=self.API_KEY)

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

        for model in self.client.models.list():
            print(model.id)

    async def update_object_key(self, key: str, telegram_id: int):
        gpt_action = await self.get_gpt_action(key=key, telegram_id=telegram_id)
        self.key = key
        self.model = gpt_action.model
        self.system_prompt = gpt_action.system_prompt
        self.max_tokens = gpt_action.max_tokens

    @classmethod
    async def get_gpt_action(cls, key: str, telegram_id: int, assistant_type = "assistant"):
        return await get_gpt_action(key, telegram_id, assistant_type)





    async def check_user_question(self, messages: list, language: str):
        for message in messages:
            if "text" not in message or message.get("role") != "user":
                continue

            if "chatgpt" in message["text"].lower() or "chat gpt" in message["text"].lower():
                return await get_localization_text(key="ask_chatgpt_answer_text",
                                                    language=language)

    def get_system_prompt(self):
        if self.system_prompt:
            return {
                "role": "system",
                "content": self.system_prompt
            }

    async def send_messages(self, messages: list, language: str, **kwargs):

        check_user_question = await self.check_user_question(messages, language=language)
        if check_user_question:
            return check_user_question

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            **kwargs
        )
        content = completion.choices[0].message.content
        return content
        # content = json.loads(content)
        # return content.get("message"), content.get("n")

    async def send_prompt(self, prompt: str | list, language: str, **kwargs):
        messages = []
        system_prompt = self.get_system_prompt()
        if system_prompt:
            messages.append(system_prompt)

        messages.append({"role": "user",
                 "content": prompt})

        return await self.send_messages(messages, language, **kwargs)


    async def send_audio(self, audio_path: str, language: str):
        with open(audio_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        os.remove(audio_path)
        return await self.send_prompt(prompt=transcript.text,
                                  language=language)

