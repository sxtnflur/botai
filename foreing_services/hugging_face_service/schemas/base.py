from abc import ABCMeta
from enum import EnumMeta, Enum


class GeneralGarmentType(str, Enum):
    upper_body = "upper_body"
    lower_body = "lower_body"
    dresses = "dresses"