import asyncio
import datetime
from typing import List, Type

from billiard.exceptions import SoftTimeLimitExceeded
from db.crud import get_cloth_categories_first_level, get_kling_tokens, add_kling_task, \
    add_one_tryon_remain_to_user, update_kling_task, add_tryon_cloth_model, get_tryon_cloth_model, get_tryon_my_photo, \
    get_tryon_my_photos, get_user_tryon_cloth_models, update_values_returning, get_localization_texts, \
    get_cloth_category, minus_request_user, plus_request_user, get_users_without_result, get_localization_text, \
    update_tryon_cloth_model
from db.schemas.try_on import ClothCategorySchema, KlingTokenSchema, GenerateTryOnResponse, GenerateTryOnStatus, \
    TryonPhotoSchema
import base64

from exceptions.try_on import ClothModelNotFound, KlingTaskNotFound
from foreing_services import (flux_service,
                              HFLeffaTryOn, GeneralGarmentType,
                              HFNymbo, FashCategory, FalGenImageIdeogram
                              )
from foreing_services import FalTryOn, FalFashnTryOn
from foreing_services.fal_service.schemas import Result, ResultFashn, FashnErrorsEnum
# from foreing_services.hugging_face_service import generate_image_task
from foreing_services.klingai_actions.schemas import TaskData, TryOnClothModelSchema, TaskStatus, CallbackProtocol, \
    KlingTaskFromDatabase, KlingTaskGet
from foreing_services.klingai_actions.try_on import KlingTryOn
from gradio_client.client import Job
from schemas.user import Gender, Language
from foreing_services import TelegramBotService
from sqlalchemy import func
from foreing_services.file_storage import BunnyCDN
from utils.formatting import image_url_to_b64, image_url_to_bytes
from celery import shared_task


def after_get_image_url(result_image_bytes: bytes, request_id: str,
                        user_telegram_id: int,
                        language: str):
    loop = asyncio.get_event_loop()

    resaved_image_url: str = loop.run_until_complete(
        BunnyCDN().upload_file_get_url(
            file=result_image_bytes, folder=BunnyCDN.folders.BOT_KLING_PHOTOS,
            filename="hfgenimg"
        )
    )

    loop.run_until_complete(update_values_returning(
        task_id=request_id,
        updates=dict(
            status="succeed",
            result_timestamp=func.now(),
            result_image=resaved_image_url,
                     )
    ))

    try_on_service = VirtualTryOn()

    loop.run_until_complete(
        try_on_service.send_message_image_result_to_bot(
            language=language,
            result_image_url=resaved_image_url,
            user_telegram_id=user_telegram_id
        )
    )


@shared_task(bind=True, time_limit=4800, soft_time_limit=3600)
def generate_image_task(self, human_image_url: str, cloth_image_url: str,
                        user_telegram_id: int, language: str,
                        vt_garment_type: GeneralGarmentType) -> None:

    try:
        ai_try_on = HFNymbo()
        job = ai_try_on.get_job_generate_image(
            human_image_url, cloth_image_url, garment_type=vt_garment_type
        )

        result_image_bytes: bytes = ai_try_on.get_result_as_bytes(job)
        after_get_image_url(
            result_image_bytes=result_image_bytes,
            request_id=self.request.id,
            user_telegram_id=user_telegram_id,
            language=language
        )

    except:
        loop = asyncio.get_event_loop()
        new_task_id: str = loop.run_until_complete(
            FalTryOn()
            .generate(human_image=human_image_url,
                      cloth_image=cloth_image_url)
        )
        loop.run_until_complete(
            update_values_returning(
                task_id=self.request.id,
                updates=dict(task_id=new_task_id,
                             generated_by_model="FAL")
            )
        )




# @shared_task(bind=True, time_limit=4800, soft_time_limit=3600)
# def generate_image_task(self, human_image_url: str, cloth_image_url: str,
#                               user_telegram_id: int, language: str,
#                         vt_garment_type: GeneralGarmentType,
#                         count_tries: int = 1) -> None:
#     max_tries = 5
#     try_sleep = 10
#
#     try:
#         ai_try_on = HFNymbo()
#         job = ai_try_on.get_job_generate_image(
#             human_image_url, cloth_image_url, garment_type=vt_garment_type
#         )
#     except:
#         if count_tries <= max_tries:
#             now = datetime.datetime.now(datetime.timezone.utc)
#
#
#             generate_image_task.apply_async(
#                 kwargs=dict(
#                     human_image_url=human_image_url,
#                     cloth_image_url=cloth_image_url,
#                     user_telegram_id=user_telegram_id,
#                     language=language,
#                     vt_garment_type=vt_garment_type,
#                     count_tries=count_tries + 1
#                 ),
#                 eta=now + datetime.timedelta(seconds=try_sleep)
#             )
#         return
#
#     try:
#         result_image_bytes: bytes = ai_try_on.get_result_as_bytes(job)
#         after_get_image_url(
#             result_image_bytes=result_image_bytes,
#             request_id=self.request.id,
#             user_telegram_id=user_telegram_id,
#             language=language
#         )
#
#     except SoftTimeLimitExceeded:
#         wait_generated_image_task.delay(human_image_url=human_image_url,
#                                         cloth_image_url=cloth_image_url,
#                                         user_telegram_id=user_telegram_id,
#                                         language=language,
#                                         vt_garment_type=vt_garment_type,
#                                         job=job)


@shared_task()
def wait_generated_image_task(self, human_image_url: str, cloth_image_url: str,
                              user_telegram_id: int, language: str,
                              vt_garment_type: GeneralGarmentType,
                              job: Job) -> None:
    try:
        ai_try_on = HFNymbo()
        result_image_bytes: bytes = ai_try_on.get_result_as_bytes(job)
        after_get_image_url(
            result_image_bytes=result_image_bytes,
            request_id=self.request.id,
            user_telegram_id=user_telegram_id,
            language=language
        )
    except SoftTimeLimitExceeded:
        wait_generated_image_task.delay(human_image_url=human_image_url,
                                        cloth_image_url=cloth_image_url,
                                        user_telegram_id=user_telegram_id,
                                        language=language,
                                        vt_garment_type=vt_garment_type,
                                        job=job)



class VirtualTryOn:
    file_storage = BunnyCDN
    telegram_bot_service = TelegramBotService()
    hugging_face = HFLeffaTryOn
    # bg_tasks = CeleryBGTasks

    async def get_cloth_categories(self) -> List[ClothCategorySchema]:
        return await get_cloth_categories_first_level()

    async def get_cloth_category(self, cloth_category_id: int) -> ClothCategorySchema:
        return await get_cloth_category(cloth_category_id=cloth_category_id)

    async def __rollback_tryon(self, user_id: int):
        # await add_one_tryon_remain_to_user(user_id=user_id)
        await plus_request_user(user_id=user_id, action="virtual-try-on")

    async def __pay_for_request(self, user_id: int, is_admin: bool) -> bool:
        if is_admin:
            return True

        model_and_requests = await minus_request_user(user_id=user_id, action="virtual-try-on")
        if model_and_requests is None:
            has_tokens = False
            model = None
        else:
            has_tokens = True
            model, requests_have = model_and_requests
        return has_tokens

    async def __generate_image(self, user_id: int,
                               human_image_b64, cloth_image_b64,
                               ) -> str | None:
        kling_tokens: List[KlingTokenSchema] = await get_kling_tokens()

        task_id: str | None = None
        for kling_token in kling_tokens:
            try:
                kling_try_on = KlingTryOn(ak=kling_token.access_key,
                                          sk=kling_token.secret_key)
                task_id: str = await kling_try_on.create_task_async(
                    human_image=human_image_b64,
                    cloth_image=cloth_image_b64
                )
            except Exception as e:
                print(e)
            else:
                break

        if not task_id:
            await self.__rollback_tryon(user_id)
            return
        return task_id

    async def __generate_image_test(self, user_id: int, human_image_url: str, cloth_image_url: str,
                                    garment_type: GeneralGarmentType) -> str | None:
        fal = FalFashnTryOn()

        if garment_type == GeneralGarmentType.upper_body:
            category = FashCategory.tops
        elif garment_type == GeneralGarmentType.lower_body:
            category = FashCategory.bottoms
        else:
            category = FashCategory.one_pieces

        request_id: str | None = await fal.generate(
            human_image=human_image_url,
            cloth_image=cloth_image_url,
            category=category
        )
        if not request_id:
            await self.__rollback_tryon(user_id)
            return
        return request_id

    async def __generate_image_hf(self, user_id: int,
                                  human_image_url: str, cloth_image_url: str,
                                  user_telegram_id: int,
                                  language: str,
                                  vt_garment_type: GeneralGarmentType) -> str | None:
        task_id: str = generate_image_task.delay(
            human_image_url=human_image_url,
            cloth_image_url=cloth_image_url,
            user_telegram_id=user_telegram_id,
            language=language,
            vt_garment_type=vt_garment_type
        ).task_id
        print(f'{task_id=}')
        if not task_id:
            await self.__rollback_tryon(user_id)
            return
        return task_id

    async def generate_image_by_human_image_past_photo(self,
                                                       user_id: int,
                                                       language: Language,
                                                       cloth_category_id: int,
                                                       kling_task_id: int,
                                                       cloth_image_b64: base64,
                                                       is_admin: bool,
                                                       user_telegram_id: int | None = None
                                                       ):
        is_has_try_on: bool = await self.__pay_for_request(user_id=user_id, is_admin=is_admin)
        if not is_has_try_on:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.client_has_not_requests)


        photo: TryonPhotoSchema | None = await self.get_tryon_my_photo(kling_task_id=kling_task_id)
        if not photo:
            await self.__rollback_tryon(user_id)
            raise KlingTaskNotFound("Task не найден")

        human_image_b64 = await image_url_to_b64(photo.human_image)

        cloth_image_bytes = base64.b64decode(cloth_image_b64)
        folder = self.file_storage.folders.BOT_KLING_PHOTOS
        cloth_photo_url = await self.file_storage().upload_file_get_url(folder=folder,
                                                                      filename=f"cloth_image_{user_id}",
                                                                      file=cloth_image_bytes)

        cloth_cat = await self.get_cloth_category(cloth_category_id)
        task_id: str | None = await self.__generate_image_test(
            user_id=user_id,
            human_image_url=photo.human_image,
            cloth_image_url=cloth_photo_url,
            garment_type=cloth_cat.garment_type
            # user_telegram_id=user_telegram_id,
            # language=language,
            # vt_garment_type=cloth_cat.garment_type
        )
        if not task_id:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.server_has_not_requests)

        await add_kling_task(
            user_id=user_id,
            task_id=task_id,
            language=language,
            human_image_from_past_task_id=kling_task_id,
            cloth_image=cloth_photo_url,
            cloth_category_id=cloth_category_id,
            user_telegram_id=user_telegram_id,
            generated_by_model="abdrabdr/IDM-VTON"
        )
        return GenerateTryOnResponse(
            task_id=task_id,
            human_image=photo.human_image,
            cloth_image=cloth_photo_url,
            status=GenerateTryOnStatus.succeed
        )

    async def generate_image_by_human_image_model_id(self,
                                                     user_id: int,
                                                     language: Language,
                                                     cloth_category_id: int,
                                                     human_image_model_id: int,
                                                     cloth_image_b64: base64,
                                                     is_admin: bool,
                                                     user_telegram_id: int | None = None,
                                                     ) -> GenerateTryOnResponse:
        is_has_try_on: bool = await self.__pay_for_request(user_id=user_id, is_admin=is_admin)
        if not is_has_try_on:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.client_has_not_requests)

        human_image: TryOnClothModelSchema | None = await self.get_tryon_cloth_model(model_id=human_image_model_id)
        if not human_image:
            await self.__rollback_tryon(user_id)
            raise ClothModelNotFound("Модель не найдена")

        # human_image_b64 = await image_url_to_b64(human_image.model_image)

        cloth_image_bytes = base64.b64decode(cloth_image_b64)
        folder = self.file_storage.folders.BOT_KLING_PHOTOS
        cloth_photo_url = await self.file_storage().upload_file_get_url(folder=folder,
                                                                      filename=f"cloth_image_{user_id}",
                                                                      file=cloth_image_bytes)

        cloth_cat = await self.get_cloth_category(cloth_category_id)
        task_id: str | None = await self.__generate_image_test(
            user_id=user_id,
           human_image_url=human_image.model_image,
         cloth_image_url=cloth_photo_url,
         garment_type=cloth_cat.garment_type
         # language=language,
         # user_telegram_id=user_telegram_id,
         # vt_garment_type=cloth_cat.garment_type
         )
        if not task_id:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.server_has_not_requests)

        await add_kling_task(
            user_id=user_id,
            task_id=task_id,
            language=language,
            human_image_model_id=human_image_model_id,
            cloth_image=cloth_photo_url,
            cloth_category_id=cloth_category_id,
            user_telegram_id=user_telegram_id,
            generated_by_model="abdrabdr/IDM-VTON"

        )
        return GenerateTryOnResponse(
            task_id=task_id,
            human_image=human_image.model_image,
            cloth_image=cloth_photo_url,
            status=GenerateTryOnStatus.succeed
        )

    async def generate_image(self,
                             user_id: int,
                             language: str,
                             cloth_category_id: int,
                             human_image: base64,
                             cloth_image: base64,
                             is_admin: bool,
                             user_telegram_id: int | None = None
                             ) -> GenerateTryOnResponse:

        is_has_try_on: bool = await self.__pay_for_request(user_id=user_id, is_admin=is_admin)
        if not is_has_try_on:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.client_has_not_requests)

        human_image_bytes = base64.b64decode(human_image)
        cloth_image_bytes = base64.b64decode(cloth_image)

        folder = self.file_storage.folders.BOT_KLING_PHOTOS
        human_photo_url = await self.file_storage().upload_file_get_url(folder=folder,
                                                                 filename=f"human_image_{user_id}",
                                                                 file=human_image_bytes)
        cloth_photo_url = await self.file_storage().upload_file_get_url(folder=folder,
                                                                 filename=f"cloth_image_{user_id}",
                                                                 file=cloth_image_bytes)

        cloth_cat = await self.get_cloth_category(cloth_category_id)
        task_id: str | None = await self.__generate_image_test(
            user_id=user_id,
            human_image_url=human_photo_url,
            cloth_image_url=cloth_photo_url,
            garment_type=cloth_cat.garment_type
             # user_telegram_id=user_telegram_id, language=language,
             # vt_garment_type=cloth_cat.garment_type
        )
        if not task_id:
            return GenerateTryOnResponse(status=GenerateTryOnStatus.server_has_not_requests)

        await add_kling_task(
            user_id=user_id,
            task_id=task_id,
            language=language,
            human_image=human_photo_url,
            cloth_image=cloth_photo_url,
            cloth_category_id=cloth_category_id,
            user_telegram_id=user_telegram_id,
            generated_by_model="abdrabdr/IDM-VTON"
        )
        return GenerateTryOnResponse(
            task_id=task_id,
            human_image=human_photo_url,
            cloth_image=cloth_photo_url,
            status=GenerateTryOnStatus.succeed
        )

    async def get_task(self, task_id: str, user_id: int) -> TaskData | None:
        kling_tokens: List[KlingTokenSchema] = await get_kling_tokens()

        task_data: TaskData | None = None
        for kling_token in kling_tokens:
            try:
                kling_try_on = KlingTryOn(ak=kling_token.access_key,
                                          sk=kling_token.secret_key)
                task_data: TaskData = await kling_try_on.get_task(task_id)
            except Exception as e:
                print(e)
            else:
                break

        if not task_data:
            return

        if task_data.task_status == TaskStatus.succeed:
            files_storage = BunnyCDN()
            try:
                resaved_image_url = await files_storage.upload_file_by_url_get_url(
                    image_url=task_data.task_result.images[0].url,
                    folder=files_storage.folders.BOT_KLING_PHOTOS
                )
            except:
                resaved_image_url = task_data.task_result.images[0].url

            task_data.task_result.images[0].url = resaved_image_url

            await update_kling_task(
                task_id=task_id,
                result_image=resaved_image_url,
                result_timestamp=func.now(),
                status=task_data.task_status
            )

        elif task_data.task_status == TaskStatus.failed:
            await self.__rollback_tryon(user_id=user_id)
            await update_kling_task(
                task_id=task_id,
                result_timestamp=func.now(),
                status=task_data.task_status
            )
        return task_data

    async def generate_image_model_by_fal(self,
                                          user_id: int,
                                          user_telegram_id: int,
                                          gender: Gender,
                                          language: str,
                                          additional_prompt: str | None = None
                                          ) -> str:
        is_male = gender.value == gender.male
        prompt = flux_service.create_prompt_for_gen_model(is_male=is_male,
                                                          prompt=additional_prompt)
        print(f'{prompt=}')
        fal = FalGenImageIdeogram()
        req_id: str = await fal.generate(prompt)
        await add_tryon_cloth_model(
            user_id=user_id,
            user_telegram_id=user_telegram_id,
            language=language,
            task_id=req_id,
            is_male=is_male,
            prompt=additional_prompt
        )
        return req_id


    async def generate_image_model(self, user_id: int,
                                   language: str,
                                   user_telegram_id: int, gender: Gender,
                                   additional_prompt: str | None) -> str:

        # Генерация изображения
        return await self.generate_image_model_by_fal(
            additional_prompt=additional_prompt, user_id=user_id, user_telegram_id=user_telegram_id,
            gender=gender, language=language
        )
        # flux = flux_service.FluxAsync()
        # generated_image: flux_service.GetResultResponse = await flux.generate_image(
        #     prompt=prompt,
        #     width=1024, height=768, is_dev=False
        # )
        # try:
        #     resaved_generated_image = await self.file_storage().upload_file_by_url_get_url(
        #         image_url=generated_image.result.sample,
        #         folder=self.file_storage.folders.BOT_MODEL_FOR_TRYON
        #     )
        # except Exception as e:
        #     print("Не удалось пересохранить изобр в наш CDN:", str(e))
        #     resaved_generated_image = generated_image.result.sample
        #
        # tryon_model: TryOnClothModelSchema = await add_tryon_cloth_model(
        #     user_id=user_id,
        #     model_image=resaved_generated_image,
        #     task_id=generated_image.id,
        #     is_male=is_male,
        #     prompt=additional_prompt
        # )
        # return tryon_model

    async def get_tryon_cloth_model(self, model_id: int) -> TryOnClothModelSchema | None:
        return await get_tryon_cloth_model(model_id=model_id)

    async def get_user_tryon_cloth_models(self, user_id: int, offset: int, limit: int) -> List[TryOnClothModelSchema]:
        return await get_user_tryon_cloth_models(user_id=user_id, offset=offset, limit=limit)

    async def get_tryon_my_photo(self, kling_task_id: int) -> TryonPhotoSchema | None:
        return await get_tryon_my_photo(kling_task_id)

    async def get_tryon_my_photos(self, user_id: int,
                                  offset: int = 0, limit: int = 10) -> List[TryonPhotoSchema]:
        return await get_tryon_my_photos(user_id=user_id, offset=offset, limit=limit)

    async def send_message_choose_cats_to_bot(self, user_telegram_id: int, language: str) -> None:
        cloth_categories = await self.get_cloth_categories()

        texts_keys = ["back", "try_on_select_cat"] + [cc.name for cc in cloth_categories]
        texts: dict[str, str] = await get_localization_texts(
            language=language,
            keys=texts_keys
        )

        inline_keyboard = [[]]
        for cc in cloth_categories:
            btn = {"text": texts.get(cc.name),
                   "callback_data": f"try_on_select_cat|{cc.id}"}
            if len(inline_keyboard[-1]) >= 2:
                inline_keyboard.append([btn])
            else:
                inline_keyboard[-1].append(btn)
        inline_keyboard.append([{"text": texts.get("back"), "callback_data": "chooseAssistant|assistant"}])

        await self.telegram_bot_service.send_text_message(
            chat_id=user_telegram_id,
            text=texts.get("try_on_select_cat"),
            inline_keyboard=inline_keyboard
        )

    async def __send_result_webhook_to_bot(self, result_image_url: str,
                                           task_id: str | None, task_status: str | None = None,
                                           filename: str = "result_image.jpg") -> None:
        # Сохраняем картинку в наш CDN, получаем ссылку / в случае ошибки сохраняем изначальную ссылку
        try:
            result_image_bytes = await image_url_to_bytes(result_image_url)

            resaved_result_image_url = await self.file_storage().upload_file_get_url(
                file=result_image_bytes, folder=self.file_storage.folders.BOT_KLING_PHOTOS,
                filename=filename
            )
            print(f'{resaved_result_image_url=}')
        except:
            resaved_result_image_url = result_image_url

        task: KlingTaskFromDatabase = await update_values_returning(
            task_id=task_id,
            updates=dict(
                status=task_status,
                result_timestamp=func.now(),
                result_image=resaved_result_image_url
            )
        )
        await self.telegram_bot_service.send_photo_message(
            chat_id=task.user_telegram_id,
            photo=resaved_result_image_url
        )
        await self.send_message_choose_cats_to_bot(
            language=task.language,
            user_telegram_id=task.user_telegram_id
        )

    async def send_error_result_webhook_to_bot(self,
                                               task_id: str,
                                               error_key: str | None = None,
                                               error_msg: str | None = None) -> None:
        task: KlingTaskFromDatabase = await update_values_returning(
            task_id=task_id,
            updates=dict(
                status="ERROR"
            )
        )
        if task.user_id:
            await self.__rollback_tryon(user_id=task.user_id)

        if error_key:
            text = await get_localization_text(language=task.language, key=error_key)
        else:
            text = await get_localization_text(language=task.language,
                                           key="tryon_generate_error")
            if error_msg:
                text += "\n" + error_msg

        await self.telegram_bot_service.send_text_message(
            chat_id=task.user_telegram_id,
            text=text
        )
        await self.send_message_choose_cats_to_bot(
            language=task.language,
            user_telegram_id=task.user_telegram_id
        )


    async def send_result_webhook_kling_to_bot(self,
                                        callback_protocol: CallbackProtocol):
        result_image_url = callback_protocol.task_result.images[0].url
        return await self.__send_result_webhook_to_bot(
            result_image_url=result_image_url, task_id=callback_protocol.task_id,
            task_status=callback_protocol.task_status
        )


    async def send_result_webhook_leffa_to_bot(self, result: Result):
        if result.status == "ERROR":
            await self.send_error_result_webhook_to_bot(
                task_id=result.request_id, error_msg=result.payload.detail
            )
        else:
            await self.__send_result_webhook_to_bot(
                result_image_url=result.payload.image.url,
                task_id=result.request_id,
                task_status=result.status
            )

    async def send_result_webhook_fal_fashn_to_bot(self, result: ResultFashn):
        if result.status == "ERROR":
            if result.payload.detail.name == FashnErrorsEnum.PoseError:
                error_key = "fashnerr_PoseError"
            elif result.payload.detail.name == FashnErrorsEnum.PhotoTypeError:
                error_key = "fashnerr_PhotoTypeError"
            else:
                return await self.send_error_result_webhook_to_bot(
                    task_id=result.request_id, error_msg=result.payload.detail.message
                )

            await self.send_error_result_webhook_to_bot(
                task_id=result.request_id, error_key=error_key
            )
        else:
            await self.__send_result_webhook_to_bot(
                result_image_url=result.payload.images[0].url,
                task_id=result.request_id,
                task_status=result.status
            )

    async def send_result_webhook_generate_image_model(self, image_url: str, task_id: str):
        # Сохраняем картинку в наш CDN, получаем ссылку / в случае ошибки сохраняем изначальную ссылку
        try:
            result_image_bytes = await image_url_to_bytes(image_url)

            resaved_result_image_url = await self.file_storage().upload_file_get_url(
                file=result_image_bytes, folder=self.file_storage.folders.BOT_KLING_PHOTOS,
                filename=str(task_id)
            )
            print(f'{resaved_result_image_url=}')
        except:
            resaved_result_image_url = image_url

        tryon_model: TryOnClothModelSchema = await update_tryon_cloth_model(
            task_id=task_id,
            model_image=resaved_result_image_url
        )

        texts = await get_localization_texts(keys=["tryon_my_generated_model",
                                                   "tryon_use_this_model",
                                                   "back"], language=tryon_model.language)
        inline_keyboard = [
            [{"text": texts.get("tryon_use_this_model"),
              "callback_data": f"tryon_use_this_model|{tryon_model.id}"}],
            [{"text": texts.get("back"),
              "callback_data": "try_on_use_model"}]
        ]

        caption = texts.get("tryon_my_generated_model").format(
            created_at=tryon_model.created_at.strftime("%H:%M %d.%m.%Y"),
            gender="🙋‍♂" if tryon_model.is_male else "🙋‍♀",
            prompt=tryon_model.prompt or "-"
        )

        await self.telegram_bot_service.send_photo_message(
            chat_id=tryon_model.user_telegram_id,
            photo=image_url,
            caption=caption,
            inline_keyboard=inline_keyboard
        )



    async def generate_image_for_users_list(self, from_datetime: datetime.datetime):
        tasks: list[KlingTaskGet] = await get_users_without_result(from_datetime=from_datetime)
        for task in tasks:
            if task.human_image_model_id:
                model: TryOnClothModelSchema | None = await self.get_tryon_cloth_model(
                    model_id=task.human_image_model_id)
                human_image = model.model_image
            else:
                human_image = task.human_image

            cat = await self.get_cloth_category(cloth_category_id=task.cloth_category_id)
            await self.__generate_image_hf(
                user_id=task.user_id,
                human_image_url=human_image,
                cloth_image_url=task.cloth_image,
                user_telegram_id=task.user_telegram_id,
                language=task.language,
                vt_garment_type=cat.garment_type
            )