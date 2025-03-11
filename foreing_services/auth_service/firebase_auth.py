from db.crud import get_user_by_firebase_uid
from firebase_admin import auth
from firebase_admin.auth import UserRecord
from firebase_conf import firebase
from schemas.user import UserMainData, FirebaseToken


class FirebaseAuth:
    async def auth_by_phone(self, phone_number: str) -> UserRecord:
        return auth.get_user_by_phone_number(phone_number)

    async def refresh_token(self, refresh_token: str) -> FirebaseToken:
        py_auth = firebase.auth()
        # Обновление токена с использованием refresh token
        new_token = py_auth.refresh(refresh_token)
        return FirebaseToken(uid=new_token['userId'],
                             refresh_token=new_token['refreshToken'],
                             token=new_token['idToken'])

    async def register_by_email(self, email: str, password: str) -> FirebaseToken:
        py_auth = firebase.auth()
        token_data: dict = py_auth.create_user_with_email_and_password(
            email, password
        )
        user = auth.get_user_by_email(email)
        return FirebaseToken(uid=user.uid,
                             refresh_token=token_data['refreshToken'],
                             token=token_data['idToken'])

    async def auth_by_email(self, email: str, password: str) -> FirebaseToken:
        py_auth = firebase.auth()
        token_data: dict = py_auth.sign_in_with_email_and_password(email, password)
        user = auth.get_user_by_email(email)
        return FirebaseToken(uid=user.uid,
                             refresh_token=token_data['refreshToken'],
                             token=token_data['idToken'])