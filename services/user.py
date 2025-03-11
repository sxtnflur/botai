from enum import Enum

from config import MAX_TRY_ON_A_DAY
from db.crud import upsert_user, get_user, update_user_data, get_user_by_firebase_uid, insert_user_by_firebase, \
    update_user_by_firebase_uid, give_starter_pack_to_user
from db.sql_models.models import User
from datetime import datetime

from firebase_admin.auth import UserRecord
from foreing_services.auth_service.firebase_auth import FirebaseAuth
from schemas.user import UserData, RegistrationStep, UpdateUser, UserMainData, FirebaseToken
from caching.redis_caching import default_cached


class UserService:

    auth = FirebaseAuth()

    async def give_starter_pack_to_user(self, user_id: int):
        await give_starter_pack_to_user(user_id)

    async def upsert_user_by_telegram(self, telegram_id: int,
                                      first_name: str,
                                      last_name: str,
                                      username: str | None,
                                      is_admin_bot: bool = False,
                                      try_on_remain: int = 0) -> UserMainData:
        user: UserMainData = await upsert_user(
            telegram_id=telegram_id, first_name=first_name,
            second_name=last_name, username=username,
            is_admin_bot=is_admin_bot, try_on_remain=try_on_remain
        )
        await self.give_starter_pack_to_user(user_id=user.id)

        return user

    async def insert_user_by_firebase(self, firebase_uid: str, phone_number: str) -> int:
        return await insert_user_by_firebase(firebase_uid=firebase_uid, phone_number=phone_number)


    async def __update_cache_for_get_user_by_firebase(self, firebase_uid: str):
        await self.__get_user_by_firebase_from_db(firebase_uid, cache_read=False, cache_write=True)

    @staticmethod
    @default_cached
    async def __get_user_by_firebase_from_db(firebase_uid: str) -> UserMainData:
        return await get_user_by_firebase_uid(firebase_uid)

    async def get_user_by_firebase(self, firebase_uid: str) -> UserMainData:
        return await self.__get_user_by_firebase_from_db(firebase_uid)

    async def auth_by_phone(self, phone_number: str) -> UserMainData:
        user_record: UserRecord = await self.auth.auth_by_phone(phone_number)
        return await self.get_user_by_firebase(firebase_uid=user_record.uid)

    async def register_by_phone(self, phone_number: str) -> int:
        user_record: UserRecord = await self.auth.auth_by_phone(phone_number)
        return await self.insert_user_by_firebase(firebase_uid=user_record.uid,
                                                  phone_number=phone_number)

    async def register_by_email(self, email: str, password: str) -> tuple[FirebaseToken, int]:
        token: FirebaseToken = await self.auth.register_by_email(email, password)
        user_id: int = await insert_user_by_firebase(firebase_uid=token.uid,
                                                    email=email)
        return token, user_id

    async def auth_by_email(self, email: str, password: str) -> FirebaseToken:
        return await self.auth.auth_by_email(email, password)

    async def refresh_token(self, refresh_token: str) -> FirebaseToken:
        return await self.auth.refresh_token(refresh_token=refresh_token)



    async def __update_cache_for_get_user_reg_data(self, telegram_id: int):
        await self.__get_user_reg_data_from_db(telegram_id, cache_read=False, cache_write=True)


    @staticmethod
    @default_cached
    async def __get_user_reg_data_from_db(telegram_id: int) -> UserMainData | None:
        return await get_user(telegram_id=telegram_id)

    @staticmethod
    async def set_reg_step_for_user(user_dict: dict) -> UserData:
        if not user_dict.get("language"):
            user_dict["registration_step"] = RegistrationStep.language
        elif not user_dict.get("sex"):
            user_dict["registration_step"] = RegistrationStep.sex
        else:
            user_dict["registration_step"] = RegistrationStep.done

            if user_dict.get("is_admin"):
                if (
                    user_dict.get("is_admin") is None
                    or (
                        user_dict.get("try_on_last_date")
                        and user_dict.get("try_on_last_date") < datetime.now()
                    )
                ):
                    user_dict["try_on_remain"] = MAX_TRY_ON_A_DAY
                else:
                    user_dict["try_on_remain"] = user_dict.get("try_on_remain")
        return UserData(**user_dict)

    async def get_user_reg_data(self,
                                telegram_id: int,
                                first_name: str,
                                last_name: str,
                                username: str | None,
                                is_admin_bot: bool = False,
                                try_on_remain: int = 0
                                ) -> UserData:
        user_reg_data: UserMainData | None = await self.__get_user_reg_data_from_db(telegram_id)
        print(f'{user_reg_data=}')
        if not user_reg_data:
            user_reg_data: UserMainData = await self.upsert_user_by_telegram(
                telegram_id, first_name, last_name, username, is_admin_bot, try_on_remain
            )
            await self.__update_cache_for_get_user_reg_data(telegram_id)

        return await self.set_reg_step_for_user(user_dict=user_reg_data.model_dump())

    async def update_user_data_by_telegram_id(self, telegram_id: int,
                                              updates: UpdateUser,
                                              returning: list[str] | None = None) -> tuple:
        update_data = {}
        for k, v in updates.model_dump().items():
            if v is not None:
                if isinstance(v, Enum):
                    v = v.value
                update_data[k] = v
        print(f"{update_data=}")
        updated_user_data: tuple = await update_user_data(telegram_id=telegram_id,
                                                          returning=returning, **update_data)
        await self.__update_cache_for_get_user_reg_data(telegram_id,
                                                        # updates=update_data
                                                        )

        return updated_user_data

    async def update_user_data_by_firebase_uid(self, firebase_uid: str,
                                               updates: UpdateUser,
                                               returning: list[str] | None) -> tuple:
        update_data = {}
        for k, v in updates.model_dump().items():
            if v is not None:
                if isinstance(v, Enum):
                    v = v.value
                update_data[k] = v
        print(f"{update_data=}")
        updated_user_data: tuple = await update_user_by_firebase_uid(firebase_uid=firebase_uid,
                                                          returning=returning, **update_data)
        await self.__update_cache_for_get_user_by_firebase(firebase_uid=firebase_uid)

        return updated_user_data