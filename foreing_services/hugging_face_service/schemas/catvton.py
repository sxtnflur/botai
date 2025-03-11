from enum import Enum

class VtGarmentType(str, Enum):
    upper_body = "upper"
    lower_body = "lower"
    dresses = "overall"


class ShowType(str, Enum):
    result_only = "result only"
    input_and_result = "input & result"
    input_and_mask_and_result = "input & mask & result"