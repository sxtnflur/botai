from foreing_services.hugging_face_service.schemas import GeneralGarmentType
from foreing_services.hugging_face_service.base import HF
from foreing_services.hugging_face_service.schemas.catvton import VtGarmentType, ShowType
from gradio_client import handle_file
from utils.formatting import convert_image_url

class HFCatVTONTryOn(HF):
    src = "zhengchong/CatVTON"

    def __predict_images_urls(self, **images):
        updated_imgs = {}
        for key, img in images.items():
            print(f'{img=}')
            updated_imgs[key] = convert_image_url(img)
        return updated_imgs

    def generate_image(self,
                       human_image_url: str,
                       cloth_image_url: str,
                       garment_type: GeneralGarmentType = GeneralGarmentType.dresses) -> str:
        # images = self.__predict_images_urls(
        #     human_image_url=human_image_url,
        #     cloth_image_url=cloth_image_url
        # )
        garment_type = getattr(VtGarmentType, garment_type)

        result = self._predict(
            person_image={"background": handle_file(human_image_url),
                          "layers": [],
                          "composite": None},
            cloth_image=handle_file(cloth_image_url),
            cloth_type=garment_type,
            guidance_scale=2.5,
            seed=42,
            show_type=ShowType.result_only,
            api_name="/submit_function"
        )
        print(f'{result=}')
        return result[0].get("url")



