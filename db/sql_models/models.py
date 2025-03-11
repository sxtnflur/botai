import datetime
from db.sql_models.tables import *
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()

class User(Base):
    __table__ = users_table

    id = users_table.c.id
    uid = users_table.c.uid
    telegram_id = users_table.c.telegram_id
    firebase_uid = users_table.c.firebase_uid
    # role_id = users_table.c.role_id
    username = users_table.c.username
    first_name = users_table.c.first_name
    second_name = users_table.c.second_name
    phone_number = users_table.c.phone_number
    email = users_table.c.email
    avatar = users_table.c.avatar
    rating = users_table.c.rating
    # region_id = users_table.c.region_id
    is_verified = users_table.c.is_verified
    is_active = users_table.c.is_active
    last_active = users_table.c.last_active

    # experience = users_table.c.experience
    # service_category_changed_date = users_table.c.service_category_changed_date
    language = users_table.c.language

    rate_id = users_table.c.rate_id
    rate_date_end = users_table.c.rate_date_end
    # rate_requests = users_table.c.rate_requests

    sex = users_table.c.sex

    is_admin_bot = users_table.c.is_admin_bot

    try_on_last_date = users_table.c.try_on_last_date
    try_on_remain = users_table.c.try_on_remain

    thread_id = users_table.c.thread_id

    model_tokens = relationship("UserTokenModel")
    rate = relationship("Rate")
    rate_models = relationship("RatesAiModels", secondary=rates_table)
    requests_groups = relationship("UserGroupRequests", primaryjoin="User.id==UserGroupRequests.user_id")

    # Связь с ролью
    # role = relationship('Role', back_populates='users')
    # Связь с регионом
    # region = relationship('Region', back_populates='users')
    # Связь с моделю менеджеров
    # store_managers = relationship("StoreManager", back_populates="user")
    # Связь с магазином
    # my_stores = relationship("Store", back_populates="owner")


class GptAction(Base):
    __table__ = gpt_actions_table

    key = gpt_actions_table.c.key
    model = gpt_actions_table.c.model
    system_prompt = gpt_actions_table.c.system_prompt

    ai_models = relationship("AiModels", secondary=actions_ai_models_table)

class Localization(Base):
    __table__ = localization_table

    key = localization_table.c.key
    ru = localization_table.c.ru
    en = localization_table.c.en
    uz = localization_table.c.uz

class Language(Base):
    __table__ = languages_table

    codename = languages_table.c.codename
    name = languages_table.c.name
    ordering = languages_table.c.ordering


class RatesAiModels(Base):
    __table__ = rates_ai_models_table

    rate_id = rates_ai_models_table.c.rate_id
    model = rates_ai_models_table.c.model


class Rate(Base):
    __table__ = rates_table

    id = rates_table.c.id
    name_id = rates_table.c.name_id
    description_id = rates_table.c.description_id
    price_rub = rates_table.c.price_rub
    price_usd = rates_table.c.price_usd
    price_uzs = rates_table.c.price_uzs
    price_stars = rates_table.c.price_stars
    max_tokens = rates_table.c.max_tokens
    limit_requests = rates_table.c.limit_requests

    name: Mapped[Localization] = relationship("Localization")
    model_groups = relationship("ModelGroup")


    # @property
    # def prices(self):
    #     return [self.price_stars, self.price_uzs]


class UserTokenModel(Base):
    __table__ = users_tokens_models_table

    user_id = users_tokens_models_table.c.user_id
    tokens = users_tokens_models_table.c.tokens
    model_id = users_tokens_models_table.c.model_id

    model = relationship("AiModels")

class AiModels(Base):
    __table__ = ai_models_table

    id = ai_models_table.c.id
    model_id = ai_models_table.c.model_id
    assistant_type = ai_models_table.c.assistant_type


class ActionAiModel(Base):
    __table__ = actions_ai_models_table

    action_key = actions_ai_models_table.c.action_key
    model_id = actions_ai_models_table.c.model_id


# NEW
class Thread(Base):
    __table__ = threads_table

    id = threads_table.c.id
    user_id = threads_table.c.user_id
    # telegram_id = threads_table.c.telegram_id
    thread_id = threads_table.c.thread_id
    created_at = threads_table.c.created_at
    name = threads_table.c.name
    action_id = threads_table.c.action_id

    user = relationship("User", foreign_keys=[user_id])


class Model(Base):
    __table__ = models_table

    id = models_table.c.id
    model = models_table.c.model
    name_id = models_table.c.name
    action = models_table.c.action

    name = relationship("Localization")

class ModelGroup(Base):
    __table__ = model_groups_table

    id = model_groups_table.c.id
    rate_id = model_groups_table.c.rate_id
    requests_limit = model_groups_table.c.requests_limit

    models = relationship(Model, secondary=model_group_members_table)


class ModelGroupMember(Base):
    __table__ = model_group_members_table

    group_id = model_group_members_table.c.group_id
    model_id = model_group_members_table.c.model_id

    group = relationship("ModelGroup")
    model = relationship("Model")

class UserGroupRequests(Base):
    __table__ = users_requests_table

    user_id = users_requests_table.c.user_id
    group_id = users_requests_table.c.group_id
    requests = users_requests_table.c.requests

    group = relationship("ModelGroup", foreign_keys=group_id)
    models = relationship("Model", secondary=model_group_members_table,
                          primaryjoin="UserGroupRequests.group_id==ModelGroupMember.group_id",
                          secondaryjoin="ModelGroupMember.model_id==Model.id"
                          )

    # user = relationship("User", foreign_keys=[telegram_id],  backref="requests_groups",
    #                     primaryjoin="User.telegram_id==UserGroupRequests.telegram_id")



class KlingTask(Base):
    __table__ = kling_tasks_table

    id = kling_tasks_table.c.id
    user_id = kling_tasks_table.c.user_id
    user_telegram_id = kling_tasks_table.c.user_telegram_id
    task_id = kling_tasks_table.c.task_id
    created_at = kling_tasks_table.c.created_at
    language = kling_tasks_table.c.language

    human_image = kling_tasks_table.c.human_image
    human_image_model_id = kling_tasks_table.c.human_image_model_id
    human_image_from_past_task_id = kling_tasks_table.c.human_image_from_past_task_id

    cloth_image = kling_tasks_table.c.cloth_image

    cloth_category_id = kling_tasks_table.c.cloth_category_id

    cloth_category = relationship("ClothCategory", foreign_keys=[cloth_category_id])

    result_image = kling_tasks_table.c.result_image
    result_timestamp = kling_tasks_table.c.result_timestamp
    status = kling_tasks_table.c.status

    generated_by_model = kling_tasks_table.c.generated_by_model



class ClothCategory(Base):
    __table__ = cloth_categories_table

    id = cloth_categories_table.c.id
    name_id = cloth_categories_table.c.name_id
    parent_id = cloth_categories_table.c.parent_id
    ordering = cloth_categories_table.c.ordering
    garment_type = cloth_categories_table.c.garment_type

    parent = relationship("ClothCategory", foreign_keys=parent_id)
    name = relationship("Localization", foreign_keys=name_id)


class AdminBotLink(Base):
    __tablename__ = "admin_bot_links"

    payload: Mapped[str] = mapped_column(primary_key=True)

class KlingToken(Base):
    __tablename__ = "kling_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_key: Mapped[str]
    secret_key: Mapped[str]
    remaining_quantity: Mapped[int|None]
    is_expired: Mapped[bool|None]


class TryonClothModel(Base):
    __table__ = kling_cloth_models

    id = kling_cloth_models.c.id
    user_id = kling_cloth_models.c.user_id
    user_telegram_id = kling_cloth_models.c.user_telegram_id
    language = kling_cloth_models.c.language
    model_image = kling_cloth_models.c.model_image
    task_id = kling_cloth_models.c.task_id
    created_at = kling_cloth_models.c.created_at
    is_male = kling_cloth_models.c.is_male
    prompt = kling_cloth_models.c.prompt

    # id: Mapped[int] = mapped_column(primary_key=True)
    # user_id: Mapped[int]
    # model_image: Mapped[str]
    # task_id: Mapped[str]
    # created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    # is_male: Mapped[bool] = mapped_column(server_default="false")
    # prompt: Mapped[str | None]


class GptAssistant(Base):
    __table__ = gpt_assistants_table

    id = gpt_assistants_table.c.id
    name = gpt_assistants_table.c.name
    description = gpt_assistants_table.c.description
    instructions = gpt_assistants_table.c.instructions
    assistant_id = gpt_assistants_table.c.assistant_id
    action_name = gpt_assistants_table.c.action_name
    action_description = gpt_assistants_table.c.action_description


class WardrobeElement(Base):
    __tablename__ = "wardrobe_elements"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    gpt_file_id: Mapped[str]
    image_url: Mapped[str]
    name: Mapped[str]
    cloth_category_id: Mapped[int] = mapped_column(ForeignKey(ClothCategory.id))
