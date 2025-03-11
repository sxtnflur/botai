from pydantic import BaseModel





class TextAllLanguagesSchema(BaseModel):
    ru: dict
    en: dict
    uz: dict

    class Config:
        from_attributes = True