import os
import dotenv
from pydantic import BaseModel

BASE_DIR = os.getcwd()

dotenv.load_dotenv()

# DATABASE
DB_PROVIDER = os.getenv("DB_PROVIDER")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# REDIS
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

# API KEYS
TG_BOT_KEY = os.environ.get('TG_BOT_KEY')
OPENAI_KEY = os.environ.get('OPENAI_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
PROVIDER_TOKEN_CLICK = os.environ.get("PROVIDER_TOKEN_CLICK")

BUNNY_CDN_API_KEY = os.environ.get("BUNNY_CDN_API_KEY")
BFL_API_KEY = os.environ.get("BFL_API_KEY")

HUGGING_FACE_API_KEY = os.environ.get("HUGGING_FACE_API_KEY")

MAX_TRY_ON_A_DAY = 5

ADMIN_IDS = [1304563494]

OPENAI_TOKENS = 1000

LEN_MESSAGES_TO_CREATE_CHAT_NAME = 2

DEFAULT_ADMIN_GPT_MODEL = "gpt-4o"

class AdminGPTSettings(BaseModel):
    tokens: int = 1000
    model: str = "gpt-4o"
    model_gen_img: str = "dall-e-3"



class DatabaseSettings(BaseModel):
    provider: str = os.getenv('DB_PROVIDER', 'postgresql+asyncpg')
    host: str = os.getenv('DB_HOST', '127.0.0.1')
    port: int = int(os.getenv('DB_PORT', 5432))
    name: str | None = os.getenv('DB_NAME')
    user: str | None = os.getenv('DB_USER')
    password: str = os.getenv('DB_PASS')

    full_url: str | None = os.getenv('DB_URL')

    @property
    def url(self) -> str:
        if self.full_url:
            return self.full_url

        return f"{self.provider}://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class ApiKeys(BaseModel):
    BUNNY_CDN: str
    ANTHROPIC: str = None
    TELEGRAM_BOT: str
    OPENAI: str
    CLICK: str
    BFL: str
    HUGGING_FACE: str

class BunnyCDN(BaseModel):
    api_key: str = os.getenv('BUNNY_CDN_API_KEY')
    storage_zone: str = os.getenv('BUNNY_CDN_STORAGE_ZONE')
    host_cdn: str = os.getenv('BUNNY_CDN_HOST_CDN')


class RedisSettings(BaseModel):
    host: str | None = os.getenv('REDIS_HOST', '127.0.0.1')
    port: int = os.getenv('REDIS_PORT', 6379)
    user: str | None = os.getenv('REDIS_USER')
    password: str | None = os.getenv('REDIS_PASSWORD')
    db: int = os.getenv('REDIS_DATABASE', 1)

    full_url: str | None = os.getenv('REDIS_URL')

    @property
    def url(self):
        if self.full_url:
            return self.full_url + f"/{self.db}"

        if self.user and self.password:
            return f'redis://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}'

    def create_url(self, db: int) -> str:
        if self.full_url:
            return self.full_url + f"/{db}"

        if self.user and self.password:
            return f'redis://{self.user}:{self.password}@{self.host}:{self.port}/{db}'
        return f'redis://{self.host}:{self.port}/{db}'


class FirebaseSettings(BaseModel):
    storage_bucket: str = os.getenv('FIREBASE_STORAGE_BUCKET')
    api_key: str = os.getenv('FIREBASE_API_KEY')
    auth_domain: str = os.getenv('FIREBASE_AUTH_DOMAIN')
    project_id: str = os.getenv('FIREBASE_PROJECT_ID')
    messaging_sender_id: str = os.getenv('FIREBASE_MESSAGING_SENDER_ID')
    app_id: str = os.getenv('FIREBASE_APP_ID')


class ConfigSettings(BaseModel):
    database: DatabaseSettings
    api: ApiKeys
    redis: RedisSettings
    admin_ai_settings: AdminGPTSettings
    cache_ttl: int = 100
    ai_trial_max_tokens: int = 1000
    stylist_api_prefix: str = os.getenv('STYLIST_API_PREFIX', "/api/dev")
    stylist_api_url: str = os.getenv('STYLIST_API_URL', "https://no-code.uz/api/dev")
    domain: str = os.getenv('DOMAIN')
    firebase: FirebaseSettings = FirebaseSettings()
    bunny_cdn: BunnyCDN = BunnyCDN()


telegram_user_cache_key = "telegramuser_{telegram_id}"

settings = ConfigSettings(
    database=DatabaseSettings(
        provider=DB_PROVIDER,
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        name=DB_NAME
    ),
    api=ApiKeys(
        BUNNY_CDN=BUNNY_CDN_API_KEY,
        ANTHROPIC=ANTHROPIC_API_KEY,
        TELEGRAM_BOT=TG_BOT_KEY,
        OPENAI=OPENAI_KEY,
        CLICK=PROVIDER_TOKEN_CLICK,
        BFL=BFL_API_KEY,
        HUGGING_FACE=HUGGING_FACE_API_KEY
    ),
    redis=RedisSettings(
        host=REDIS_HOST,
        port=REDIS_PORT
    ),
    admin_ai_settings=AdminGPTSettings(tokens=1000)
)


text_timedeltas = {
    "ru": {
        "d": "дн",
        "h": "ч",
        "m": "мин",
        "s": "сек"
    },
    "en": {
        "d": "d",
        "h": "h",
        "m": "min",
        "s": "sec"
    },
    "uz": {
        "d": "kun",
        "h": "soat",
        "m": "daqiqa",
        "s": "soniya"
    }
}

CONTENT_CREATE_THREAD_NAME = """
Придумай короткое название (до 19 символов) нашему диалогу на том языке, на котором мы общались.
В твоем ответе должно быть только название, не используй спецсимволы
"""

ASSISTANT_NAME = "Assistant Stylist"

ASSISTANT_INSTRUCTIONS = """
You are a professional fashion stylist bot with expert knowledge in modern trends, fashion advice, and styling tips.
You specialize in helping users create stylish looks, select outfits, and refine their personal style.
Only answer questions directly related to fashion, styling, outfit selection, clothing brands, color coordination, 
and accessories. Politely refuse to answer any questions that are unrelated to fashion or styling.
You can use previous images that have ever been sent to you for clothing recommendations.
"""


ASSISTANT_IDS = {
    1: {
        "id": "asst_41xKyaFfjQ1ZyoWir1I5KFEP",
        "name": "Assistant Stylist",
        "description": "An assistant who gives users style recommendations",
        "instructions": ASSISTANT_INSTRUCTIONS
    },
    2: {
        "id": "asst_A8BJv49LggctyEQ4XD06E3xy",
        "name": "Assistant Stylist (Send My Photo)",
        "description": "An assistant who gives recommendations for improving style based "
                       "on photos of their appearance from users",
        "instructions": ASSISTANT_INSTRUCTIONS + """
Users send you their photos, and you have to give an assessment and advice on style and fashion for the user based on this photo
""",
    },
    3: {
        "id": "asst_upSSieUKlpltIpwgZGoTbB3C",
        "name": "Assistant Stylist (Set Of Clothes)",
        "description": "An assistant who gives recommendations on how to improve a set of clothes",
        "instructions": ASSISTANT_INSTRUCTIONS + """
Users send you photos of their set of clothes in separate photos.
You should consider these photos as a set of clothes and give an assessment and recommendations for improving the set.
"""
    }
}

LANGUAGE_CAPTIONS = {
    "ru": "Дай ответ на русском языке",
    "en": "Give me an answer in English",
    "uz": "O'zbek tilida javob bering"
}

ACTIONS = {
    1: "get_recommendation",
    2: "send_my_photo",
    3: "send_look_photos"
}
