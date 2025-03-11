import random
from enum import Enum

from foreing_services.hugging_face_service.schemas import GeneralGarmentType
from foreing_services.hugging_face_service.base import HF
from gradio_client import file
from gradio_client.client import Job


class GarmentDescription(str, Enum):
    upper_body = "Upper body"
    lower_body = "Lower body"
    dresses = "Full-body clothing"


class HFNymbo(HF):
    src = "abdrabdr/IDM-VTON"

    settings = dict(
        is_checked=True,
        is_checked_crop=True,
        denoise_steps=40,
        api_name="/tryon"
    )

    def __get_params(self, human_image_url: str,
                           cloth_image_url: str,
                           garment_type: GeneralGarmentType | None = None,
                           garment_des: str | None = None) -> dict:
        try:
            garment_type_des =getattr(GarmentDescription, garment_type)
        except:
            garment_type_des = None
        return dict(
            dict={
                "background": file(human_image_url),
                "layers": [], "composite": None},
            garm_img=file(cloth_image_url),
            garment_des=garment_des or garment_type_des,
            seed=random.randint(1, 999),
            **self.settings
        )

    def get_job_generate_image(self,
                               human_image_url: str,
                               cloth_image_url: str,
                               garment_type: GeneralGarmentType | None = None,
                               garment_des: str | None = None
                               ) -> Job:
        params = self.__get_params(human_image_url, cloth_image_url,
                                                      garment_type, garment_des)
        print(f'{params=}')
        return self.client.submit(**params)

    def generate_image(self,
                       human_image_url: str,
                       cloth_image_url: str,
                       garment_type: GeneralGarmentType,
                       garment_des: str | None = None) -> str:
        params = self.__get_params(human_image_url, cloth_image_url,
                                   garment_type, garment_des)
        print(f'{params=}')
        res = self._predict(**params)
        print(f'{res=}')
        return res[0].get("url")


