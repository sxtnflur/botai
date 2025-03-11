from typing import Text, List

from config import CONTENT_CREATE_THREAD_NAME, LEN_MESSAGES_TO_CREATE_CHAT_NAME
from foreing_services.gpt_actions.main_ import ChatGPT4
from openai import AsyncAssistantEventHandler
from schemas.gpt import FilePurpose
from openai.types.beta.threads import TextDelta, Message
from typing_extensions import override

class Assistant(ChatGPT4):
    # assistant_id = ASSISTANT_ID
    assistant_id = None
    action: str | None = None

    async def create_new_assistant(self, name=None, description=None, instructions=None):
        assistant = await self.client.beta.assistants.create(
            model=self.model,
            name=name,
            description=description,
            instructions=instructions
        )
        return assistant


    async def update_assistant_data(self, assistant_id: str, **kwargs):
        await self.client.beta.assistants.update(
            assistant_id=assistant_id,
            **kwargs
        )

    async def get_all_assistants(self):
        assistants = await self.client.beta.assistants.list()
        return assistants

    async def create_new_thread(self) -> str:
        thread = await self.client.beta.threads.create()
        return thread.id

    async def get_last_message(self, thread_id: str):
        async for message in self.client.beta.threads.messages.list(
            thread_id=thread_id
        ):
            print(f"{message.role=}")
            print(f"{message.content=}")
            if message.role == "assistant":
                return message.content[0].text.value

    async def get_message_by_id(self, thread_id: str, message_id: str) -> Message:
        return await self.client.beta.threads.messages.retrieve(
            message_id=message_id,
            thread_id=thread_id
        )

    async def get_thread_messages(self, thread_id: str,
                                  offset_message_id: str | None = None,
                                  limit: int = 20) -> List[Message]:
        data: dict = dict(
            thread_id=thread_id,
            order="desc"
        )
        if offset_message_id:
            data.update(after=offset_message_id)
        if limit:
            data.update(limit=limit)

        messages = []
        async for message in self.client.beta.threads.messages.list(**data):
            messages.append(message)

        return messages

    async def get_thread(self, thread_id: str):
        return await self.client.beta.threads.retrieve(thread_id=thread_id)

    async def create_chat_name(self, thread_id: str):
        print("START CREATE CHAT NAME")
        num_messages = 0
        async for i in self.client.beta.threads.messages.list(thread_id=thread_id,
                                                              limit=LEN_MESSAGES_TO_CREATE_CHAT_NAME):
            print(f"{i.role=}")
            if i.role == "assistant":
                num_messages += 1

        print("NUM MESSAGES:", num_messages)
        if num_messages == LEN_MESSAGES_TO_CREATE_CHAT_NAME:
            print("CREATE CHAT NAME")
            for name in await self.send_content_poll(content=CONTENT_CREATE_THREAD_NAME,
                                                     thread_id=thread_id):

                return name


    async def send_content_poll(self, content: str|list, thread_id: str) -> str:
        await self.client.beta.threads.messages.create(
            thread_id=thread_id,
            content=content,
            role="user"
        )

        run = await self.client.beta.threads.runs.create_and_poll(
            assistant_id=self.assistant_id,
            thread_id=thread_id,
            max_completion_tokens=self.max_tokens
        )
        print(f'{run.status=}')
        print(f'{run.incomplete_details=}')
        print(f'{run.last_error=}')
        if run.status == "completed":
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                run_id=run.id,
            )
            async for message in messages:
                print(f'{message=}')
                if message.role == "assistant":
                    for block in message.content:
                        if block.type == "text":
                            return block.text.value


    async def __get_or_create_vector_store(self, name: str):
        async for existing_vector_store in await self.client.beta.vector_stores.list():
            if existing_vector_store.name == name:
                return existing_vector_store
        return await self.client.beta.vector_stores.create(name=name)

    async def __upload_images_to_thread_wardrobe(self, image: bytes, filename: str) -> int:
        file = await self.client.files.create(file=(filename, image), purpose=FilePurpose.vision.value)
        return file.id

    async def upload_images_to_thread_wardrobe(self, image: bytes, thread_id: str,
                                               filename: str,
                                               vector_storage_name: str | None = None) -> int:
        await self.get_files()
        return await self.__upload_images_to_thread_wardrobe(image, filename)
        # thread = await self.get_thread(thread_id)
        #
        # vectore_store = await self.__get_or_create_vector_store(name=vector_storage_name or thread_id)
        # print(f'{vectore_store.file_counts=}')
        #
        # file_batch = await self.client.beta.vector_stores.file_batches.upload_and_poll(
        #     vector_store_id=vectore_store.id,
        #     files=images
        # )
        # print(f'{file_batch.file_counts=}')
        #
        # if thread.tool_resources.file_search.vector_store_ids in (None, []):
        #     await self.client.beta.threads.update(
        #         thread_id=thread_id,
        #         tool_resources={
        #             "file_search": {
        #                 "vector_store_ids": [vectore_store.id]
        #             }
        #         }
        #     )

    async def delete_file(self, file_id: str) -> None:
        await self.client.files.delete(file_id=file_id)

    async def get_files(self):
        files = []
        async for file in self.client.files.list():
            print(f'{file=}')
            files.append(file)
        return files

    async def delete_not_needed_files(self, not_delete: list[str]):
        async for file in self.client.files.list():
            print(f'{file=}')
            if file.id not in not_delete:
                print("DELETE")
                await self.delete_file(file_id=file.id)


class EventHandler(AsyncAssistantEventHandler):
    @override
    async def on_text_created(self, text: Text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    async def on_text_delta(self, delta: TextDelta, snapshot: Text) -> None:
        print(delta.value, end="", flush=True)


class AssistantStream(Assistant):
    @override
    def __init__(self, thread_id: str, **kwargs):
        self.thread_id = thread_id
        super(AssistantStream, self).__init__(**kwargs)
        print("MY MODEL:", self.model)

    async def stream(self, content: str|dict):
        await self.client.beta.threads.messages.create(
            thread_id=self.thread_id,
            role="user",
            content=content,
        )

        async with self.client.beta.threads.runs.stream(
                assistant_id=self.assistant_id,
                thread_id=self.thread_id,
                model=self.model,
                max_prompt_tokens=self.max_tokens,
                max_completion_tokens=self.max_tokens
                # event_handler=EventHandler()
        ) as stream:
            async for chunk in stream.__stream__():
                try:
                    yield chunk.data.delta.content[0].text.value
                except:
                    pass