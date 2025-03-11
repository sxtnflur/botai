import enum

from db.sql_models.types import IntEnum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, MetaData, Table, JSON, Text, \
    SmallInteger, func, BigInteger, Date, Enum

# Создание экземпляра MetaData
metadata = MetaData()

# Определение таблицы 'users'
users_table = Table(
    'users',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('uid', String(255), unique=True, nullable=False),
    Column('telegram_id', BigInteger(), unique=True, nullable=True),
    Column('firebase_uid', String, nullable=True),
    # Column('role_id', Integer, ForeignKey('roles.id')),
    Column('username', String(255), nullable=True),
    Column('first_name', String(255), nullable=True),
    Column('second_name', String(255), nullable=True),
    Column('phone_number', String(255), nullable=True),
    Column('email', String(255), nullable=True, unique=True),
    Column('avatar', String(255), nullable=True),
    Column('rating', Float, nullable=True),
    # Column('region_id', Integer, ForeignKey('regions.id'), nullable=True),
    Column('is_verified', Boolean, default=False),
    Column('is_active', Boolean, default=True),
    Column('created_at', DateTime, nullable=False, server_default=func.now()),
    Column('last_active', DateTime, nullable=False, server_default=func.now()),
    # Column('experience', JSON, nullable=True),
    # Column('service_category_changed_date', DateTime, nullable=True),
    Column('language', String(2), nullable=True),

    Column('rate_id', Integer, ForeignKey("rates.id"), nullable=True),
    Column('rate_date_end', DateTime, nullable=True),
    # Column('rate_requests', Integer, default=0),
    Column('sex', String(1), nullable=True),
    Column('is_admin_bot', Boolean(), server_default="false"),
    Column('try_on_last_date', Date(), nullable=True, server_default="null"),
    Column('try_on_remain', SmallInteger(), server_default="0"),
    Column('thread_id', String, nullable=True)
)

gpt_actions_table = Table(
    'gpt_actions',
    metadata,
    Column('key', String(30), primary_key=True, nullable=False),
    Column('model', String(30), nullable=False),
    Column('system_prompt', Text(), nullable=True)
)


localization_table = Table(
    'localization',
    metadata,
    Column('key', String(50), primary_key=True, nullable=False),
    Column('en', Text(), nullable=False),
    Column('ru', Text(), nullable=False),
    Column('uz', Text(), nullable=False),
)

languages_table = Table(
    'languages',
    metadata,
    Column('codename', String(2), primary_key=True),
    Column('name', String(20), nullable=False),
    Column("ordering", SmallInteger, nullable=True)
)


rates_table = Table(
    'rates',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('name_id', String(50), ForeignKey("localization.key")),
    Column('description_id', String(50)),
    Column('price_rub', Integer),
    Column('price_usd', Integer),
    Column('price_uzs', Integer),
    Column('price_stars', Integer),
    Column('max_tokens', Integer),
    Column('limit_requests', Integer)
)


# gpt_actions_rates = Table(
#     'gpt_actions_rates',
#     metadata,
#     Column('gpt_action_key', String(30), nullable=False),
#     Column('rate_id', Integer(), nullable=False)
# )



rates_ai_models_table = Table(
    'rates_ai_models',
    metadata,
    Column('rate_id', Integer, ForeignKey('rates.id'), nullable=False, primary_key=True),
    Column('model', String(50), nullable=False, primary_key=True),
)

users_tokens_models_table = Table(
    'users_tokens_models',
    metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('tokens', Integer),
    Column('model_id', Integer, ForeignKey('ai_models.id'), primary_key=True)
)

ai_models_table = Table(
    'ai_models',
    metadata,
    Column('id', Integer, primary_key=True),
    Column('model_id', String(30), nullable=False, unique=True),
    Column('assistant_type', String(50), nullable=False)
)

actions_ai_models_table = Table(
    'actions_ai_models',
    metadata,
    Column('action_key', String(30), ForeignKey("gpt_actions.key"), primary_key=True),
    Column('model_id', Integer, ForeignKey("ai_models.id"), primary_key=True)
)


# NEW
threads_table = Table(
    "threads",
    metadata,
    Column("id", Integer, primary_key=True, nullable=False),
    Column("user_id", BigInteger, ForeignKey("users.id"), nullable=False),
    Column("thread_id", String(255), nullable=False),
    Column("created_at", DateTime, nullable=False, default=func.now()),
    Column("name", String, nullable=True),
    Column("action_id", Integer, nullable=True)
)

models_table = Table(
    "models",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(255), ForeignKey("localization.key"), nullable=False),
    Column("action", String(50), nullable=False),
    Column("model", String(50), nullable=False)
)

model_groups_table = Table(
    "model_groups",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("rate_id", Integer, ForeignKey("rates.id"), nullable=True),
    Column("requests_limit", Integer, nullable=False)
)

model_group_members_table = Table(
    "model_group_members",
    metadata,
    Column("group_id", Integer, ForeignKey("model_groups.id"), primary_key=True, nullable=False),
    Column("model_id", Integer, ForeignKey("models.id"), primary_key=True, nullable=False)
)

users_requests_table = Table(
    "users_ai_requests",
    metadata,
    Column("user_id", BigInteger, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("model_groups.id"), primary_key=True),
    Column("requests", Integer, primary_key=True, nullable=False)
)



kling_tasks_table = Table(
    "kling_tasks",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer),
    Column("user_telegram_id", BigInteger, nullable=True),
    Column("task_id", String),
    Column("created_at", DateTime, server_default=func.now()),
    Column("language", String(2)),
    Column("human_image", String(255), nullable=True),
    Column("human_image_model_id", Integer, ForeignKey("tryon_cloth_models.id"), nullable=True),
    Column("human_image_from_past_task_id", Integer, ForeignKey("kling_tasks.id"), nullable=True),
    Column("cloth_image", String(255)),
    Column("cloth_category_id", Integer, ForeignKey("cloth_categories.id")),
    Column("result_image", String, nullable=True),
    Column("result_timestamp", DateTime, nullable=True),
    Column("status", String, nullable=True),
    Column("generated_by_model", String, nullable=True)
)

kling_cloth_models = Table(
    "tryon_cloth_models",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_telegram_id", BigInteger, nullable=True),
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("language", String(2), nullable=True),
    Column("model_image", String(255), nullable=True),
    Column("task_id", String),
    Column("created_at", DateTime, server_default=func.now()),
    Column("is_male", Boolean, server_default="false"),
    Column("prompt", Text, nullable=True)
)


class GarmentType(enum.Enum):
    upper_body = 0
    lower_body = 1
    dresses = 2


cloth_categories_table = Table(
    "cloth_categories",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name_id", String(255), ForeignKey("localization.key")),
    Column("parent_id", Integer, ForeignKey("cloth_categories.id"), nullable=True),
    Column("garment_type", IntEnum(GarmentType)),
    Column("ordering", SmallInteger)
)


gpt_assistants_table = Table(
    "gpt_assistants",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String),
    Column("description", Text),
    Column("instructions", Text),
    Column("assistant_id", String),
    Column("action_name", String),
    Column("action_description", String)
)