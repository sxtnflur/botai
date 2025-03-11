import firebase_admin
import pyrebase
from firebase_admin import credentials
from firebase_admin import db
from config import settings

cred = credentials.Certificate('firebase_config_json/firebase_config.json')
firebase_admin.initialize_app(cred, {
    'storageBucket': settings.firebase.storage_bucket
})

# Инициализация pyrebase
firebase_config = {
    "apiKey": settings.firebase.api_key,
    "authDomain": settings.firebase.auth_domain,
    "projectId": settings.firebase.project_id,
    "storageBucket": settings.firebase.storage_bucket,
    "messagingSenderId": settings.firebase.messaging_sender_id,
    "appId": settings.firebase.app_id
}

firebase = pyrebase.initialize_app(firebase_config)