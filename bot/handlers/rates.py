from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from config import settings, ADMIN_IDS
from db.crud import get_user_language, get_localization_text, get_localization_texts
from bot.keyboards import create_buttons_rates, create_buttons_payways_rate, create_kb_no_translate, get_btn_back, create_kb
from schemas.rate import RateSchema
from schemas.user import UserData, UserRateData
from services import rate_service
from bot.utils.messages import send_message, get_message

router = Router()


@router.callback_query(F.data.startswith("rates|"))
async def start_rates(call: CallbackQuery, user_data: UserData):
    rate: UserRateData = await rate_service.get_user_rate(user_id=user_data.id)
    print(f'{rate=}')
    btns, keys, my_rate_name_id = await create_buttons_rates(my_rate_id=rate.rate_id)

    message_data = await get_message(
        message_key="rates_text",
        inline_keyboard=btns,
        inline_keyboard_keys=keys,
        language=user_data.language
    )

    if my_rate_name_id:
        message_data["text"] += "\n\n" + (
            await get_localization_text(key="my_current_rate", language=user_data.language)
        ).format(
            my_rate_name=await get_localization_text(key=my_rate_name_id, language=user_data.language),
            my_rate_date_end=str(rate.rate_date_end)
        )

    await send_message(message_data=message_data, call=call)


@router.callback_query(F.data.startswith("choose_rate|"))
async def choose_rate(call: CallbackQuery, user_data: UserData):
    rate_id = int(call.data.split("|")[1])

    rate: RateSchema = await rate_service.get_rate(rate_id=rate_id, user_id=user_data.id)
    print(f'{rate=}')
    text_keys = []
    for mg in rate.model_groups:
        for m in mg.models:
            if m.name:
                text_keys.append(m.name)
    localization_texts: dict = await get_localization_texts(keys=text_keys, language=user_data.language)

    requests_text = []
    for mg in rate.model_groups:
        requests = {"requests_limit": mg.requests_limit}
        for model in mg.models:
            if model.name:
                requests.setdefault("name", []).append(localization_texts.get(model.name))
        print(f'{requests=}')
        requests_text.append(f"<b>{', '.join(requests.get('name'))}</b>: {requests.get('requests_limit')}")
    print(f'{requests_text=}')
    requests_text = "\n".join(requests_text)

    print("START MESSAGE")
    message = await get_message(
        message_key=rate.description,
        inline_keyboard=[
            [{"text": "buy_rate", "callback_data": f"payment|rate|{rate_id}"}],
            [{"text": "back", "callback_data": f"rates|no"}]
        ],
        inline_keyboard_keys=["buy_rate", "back"],
        language=user_data.language
    )
    print(f'{message=}')
    my_rate_info = None
    if rate.is_mine:
        rate: UserRateData = await rate_service.get_user_rate(user_id=user_data.id)

        my_rate_info = (await get_localization_text(key="my_rate", language=user_data.language)).format(
            rate_date_end=str(rate.rate_date_end)
        )

    message["text"] = message["text"].format(
        requests_limits=requests_text,
        my_rate_info=my_rate_info or ""
    )

    await send_message(message_data=message, call=call)


@router.callback_query(F.data.startswith("payment|"))
async def payment(call: CallbackQuery, user_data: UserData):
    purchase_type = call.data.split("|")[1]
    language = await get_user_language(call.from_user.id)
    if purchase_type == "rate":
        rate_id = int(call.data.split("|")[2])
        rate: RateSchema = await rate_service.get_rate(rate_id=rate_id, user_id=user_data.id)
        btns = await create_buttons_payways_rate(rate=rate)

        kb = await create_kb_no_translate(btns)
        kb.inline_keyboard.append([await get_btn_back(language, f"choose_rate|{rate_id}")])

        await call.message.edit_reply_markup(reply_markup=kb)

@router.callback_query(F.data.startswith("pay|"))
async def pay(call: CallbackQuery, user_data: UserData):
    purchase_type = call.data.split("|")[1]
    language = await get_user_language(call.from_user.id)
    if purchase_type == "rate":
        rate_id = int(call.data.split("|")[2])
        payment_service = call.data.split("|")[3]

        rate: RateSchema = await rate_service.get_rate(rate_id=rate_id, user_id=user_data.id)
        rate_name = await get_localization_text(key=rate.name, language=language)
        # rate = (await get_rate_prices(rate_id, name_by_language=language))

        if payment_service == "stars":
            currency = "XTR"
            provider_token = ""
            labeled_price_data = {
                "label": "Telegram Stars",
                "amount": rate.price_stars
            }
        elif payment_service == "click":
            currency = "UZS"
            provider_token = settings.api.CLICK
            labeled_price_data = {
                "label": "UZS",
                "amount": rate.price_uzs * 100
            }
        else:
            return

        print(provider_token)

        invoice_link = await call.bot.create_invoice_link(
            title=rate_name,
            description=rate_name,
            currency=currency,
            provider_token=provider_token,
            payload=f"rate|{rate_id}|{payment_service}",
            prices=[
                LabeledPrice(
                    **labeled_price_data
                )
            ]
        )

        kb = await create_kb(
            buttons=[
                [{"text": "buy_rate", "pay": True, "url": invoice_link}],
                [{"text": "back", "callback_data": f"payment|{purchase_type}|{rate_id}"}]
            ],
            keys=["buy_rate", "back"],
            language=language
        )

        await call.message.edit_reply_markup(
            reply_markup=kb
        )


@router.pre_checkout_query()
async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    print(pre_checkout_query.invoice_payload)
    print(pre_checkout_query.order_info)
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def get_payment(invoice, m: Message, user_data: UserData):
    type_purchase, purchase_id, payment_service = invoice.split("|")
    purchase_id = int(purchase_id)

    if type_purchase == "rate":
        await rate_service.give_rate_to_user(user_id=user_data.id,
                                             rate_id=purchase_id)
        rate: RateSchema = await rate_service.get_rate(rate_id=purchase_id, user_id=user_data.id)
        rate_name = await get_localization_text(key=rate.name, language=user_data.language)

        message_data = await get_message(
            message_key="successful_buy_rate",
            inline_keyboard=[
                [{"text": "back_to_menu", "callback_data": "change_assistant"}]
            ],
            inline_keyboard_keys=["back_to_menu"],
            language=user_data.language
        )
        message_data["text"] = message_data["text"].format(rate=rate_name)
        await send_message(message_data=message_data, message=m)


@router.message(F.successful_payment)
async def get_payment_handler(m: Message, user_data: UserData):
    invoice = m.successful_payment.invoice_payload
    print(invoice)
    await get_payment(invoice, m, user_data)

@router.message(F.text.startswith("set_rate "))
async def test_buy(m: Message, user_data: UserData):
    if user_data.is_admin:
        rate_id = m.text.split()[1]
        invoice = f"rate|{rate_id}|stars"
        await get_payment(invoice=invoice, m=m, user_data=user_data)