from typing import List

from aiogram.types import Message, InlineKeyboardMarkup
from config import LANGUAGE_CAPTIONS
from gpt_actions.assistant import AssistantStream
from gpt_actions.main_ import ChatGPT4
from gpt_actions.vision import ChatGPTVision
from utils.formatting import tg_photo_to_url, save_voice_as_mp3


def fix_gpt_md_text(text: str) -> str:
    md_symbols = ("**", "```", "__")

    for symb in md_symbols:
        if symb not in text:
            continue

        count_symb_in_text = text.count(symb)
        if count_symb_in_text > 0 and count_symb_in_text % 2 == 0:
            return text + symb

    return text


async def get_content_from_message(message: Message, album: List[Message] = None, language: str|None = None):
    if message.text:
        return message.text
    elif message.voice:
        audio_path = await save_voice_as_mp3(voice=message.voice)
        gpt = ChatGPT4()
        return await gpt.transcript_audio(audio_path=audio_path)
    elif message.media_group_id and album:
        photo_urls = []
        for album_msg in album:
            photo_urls.append(await tg_photo_to_url(album_msg))

        gpt = ChatGPTVision()
        caption = message.caption or (LANGUAGE_CAPTIONS.get(language) if language else None)
        return gpt.create_content(
            photo_urls=photo_urls, caption=caption
        )
    elif message.photo:
        gpt = ChatGPTVision()
        photo_url = await tg_photo_to_url(message)
        print(f"{photo_url=}")
        caption = message.caption or (LANGUAGE_CAPTIONS.get(language) if language else None)
        return gpt.create_content(photo_urls=[photo_url], caption=caption)
    else:
        return

async def get_gpt_action(message: Message):
    if message.text:
        return "text"
    elif message.voice:
        return "text"
    elif message.media_group_id:
        return "vision"
    elif message.photo:
        return "vision"


async def send_message_assistant(content, message: Message, assistant_stream: AssistantStream,
                                 reply_markup: InlineKeyboardMarkup):
    i = 1
    bot_msg: Message = None
    full_text = ""
    len_split = 1

    print(f"{content=}")

    async for chunk in assistant_stream.stream(content):
        full_text += chunk
        # print(chunk, end="")
        if i:
            try:
                bot_msg: Message = await message.answer(text=chunk + "...", reply_markup=reply_markup,
                                                  parse_mode="Markdown")
            except Exception as e:
                print("ERROR START:", e)
            else:
                i = 0
        elif len(full_text.split("\n")) > len_split:
            len_split = len(full_text.split("\n"))
            try:
                bot_msg: Message = await bot_msg.edit_text(text=fix_gpt_md_text(full_text) + "...",
                                                           reply_markup=reply_markup,
                                                           parse_mode="Markdown")
            except Exception as e:
                print(e)

    try:
        await bot_msg.edit_text(text=fix_gpt_md_text(full_text),
                                reply_markup=reply_markup,
                                parse_mode="Markdown")
    except Exception as e:
        print("ERROR END:", e)