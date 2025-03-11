import random

from foreing_services.hugging_face_service.schemas import GeneralGarmentType
from foreing_services.hugging_face_service.schemas.leffa import ResultImage, VtGarmentType
from foreing_services.hugging_face_service.base import HF
from gradio_client import handle_file


class HFLeffaTryOn(HF):
    src = "franciszzj/Leffa"
    # @staticmethod
    # def generate_image_static(
    #                     human_image_url: str,
    #                     cloth_image_url: str,
    #                     vt_garment_type: VtGarmentType = VtGarmentType.upper_body
    #                  ) -> ResultImage:
    #     result = _get_client().predict(
    #         src_image_path=handle_file(human_image_url),
    #         ref_image_path=handle_file(cloth_image_url),
    #         ref_acceleration=False,
    #         step=50,
    #         scale=2.5,
    #         seed=random.randint(1, 100),
    #         vt_model_type="viton_hd",
    #         vt_garment_type=vt_garment_type,
    #         vt_repaint=False,
    #         api_name="/leffa_predict_vt"
    #     )
    #     result: dict = result[0]
    #     return ResultImage(**result)

    def generate_image(self,
                     human_image_url: str,
                     cloth_image_url: str,
                     garment_type: GeneralGarmentType = GeneralGarmentType.upper_body
                     ) -> str:
        garment_type = getattr(VtGarmentType, garment_type)
        result = self._predict(
            src_image_path=handle_file(human_image_url),
            ref_image_path=handle_file(cloth_image_url),
            ref_acceleration=False,
            step=50,
            scale=2.5,
            seed=random.randint(1, 100),
            vt_model_type="viton_hd",
            vt_garment_type=garment_type,
            vt_repaint=False,
            api_name="/leffa_predict_vt"
        )
        # result = self.client.predict(
        #     src_image_path=handle_file(human_image_url),
        #     ref_image_path=handle_file(cloth_image_url),
        #     ref_acceleration=False,
        #     step=50,
        #     scale=2.5,
        #     seed=random.randint(1, 100),
        #     vt_model_type="viton_hd",
        #     vt_garment_type=vt_garment_type,
        #     vt_repaint=False,
        #     api_name="/leffa_predict_vt"
        # )
        result = ResultImage(**result[0])
        return result.url