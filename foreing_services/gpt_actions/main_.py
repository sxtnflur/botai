from config import settings, OPENAI_TOKENS
from openai import AsyncOpenAI
import os



class ChatGPT4:
    API_KEY = settings.api.OPENAI
    key = "text"
    telegram_id = None
    model = "gpt-4o-mini"
    max_tokens = OPENAI_TOKENS
    system_prompt = None

    def __init__(self, **kwargs):
        self.client = AsyncOpenAI(api_key=self.API_KEY)
        for k, v in kwargs.items():
            self.__setattr__(k, v)

    async def get_system_prompt(self):
        if self.system_prompt:
            return {
                "role": "system",
                "content": self.system_prompt
            }

    async def check_user_text(self, text: str) -> bool:
        print("TEXT:", text)
        for trigger_word in ("chatgpt", "chat gpt", "чат джипити"):
            if trigger_word in text:
                return True

        return False

    async def check_user_content(self, content: str|list) -> bool:
        if isinstance(content, str):
            check = await self.check_user_text(text=content.lower())
            if check:
                return check
        else:
            for c in content:
                text = c.get("text")
                if text:
                    check = await self.check_user_text(text=text.lower())
                    if check:
                        return check

    async def check_user_messages(self, messages: list):
        for message in messages:
            print("MESSAGE:", message)
            if "content" not in message or message.get("role") != "user":
                continue
            return await self.check_user_content(content=message["content"])




    async def send_messages(self, messages: list, **kwargs) -> str:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            **kwargs
        )
        content = completion.choices[0].message.content
        return content

    async def create_messages(self, content: str | list):
        messages = []
        system_prompt = await self.get_system_prompt()
        if system_prompt:
            messages.append(system_prompt)

        messages.append({"role": "user",
                         "content": content})
        return messages

    async def send_prompt(self, prompt: str | list, language: str, **kwargs):
        messages = []
        system_prompt = await self.get_system_prompt()
        if system_prompt:
            messages.append(system_prompt)

        messages.append({"role": "user",
                 "content": prompt})

        return await self.send_messages(messages, language, **kwargs)

    async def send_messages_stream(self, messages: list, **kwargs):
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            stream=True,
            **kwargs
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None and chunk.choices[0].delta.content != "":
                yield chunk.choices[0].delta.content


    async def send_prompt_stream(self, prompt: str | list, **kwargs):
        messages = []
        system_prompt = await self.get_system_prompt()
        if system_prompt:
            messages.append(system_prompt)

        messages.append({"role": "user",
                         "content": prompt})

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            stream=True,
            **kwargs
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None and chunk.choices[0].delta.content != "":
                yield chunk.choices[0].delta.content

    async def transcript_audio(self, audio_path: str):
        with open(audio_path, "rb") as audio_file:
            transcript = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        os.remove(audio_path)
        return transcript.text

    async def transcript_audio_by_bytes(self, audio: bytes | tuple[str, bytes]) -> str:
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio
        )
        return transcript.text

    async def _(self):
        print(self.client.user_agent)
        self.client.beta.chat