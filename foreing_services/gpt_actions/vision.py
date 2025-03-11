from foreing_services.gpt_actions.main_ import ChatGPT4


class ChatGPTVision(ChatGPT4):
    model = "gpt-4o-mini"

    def create_content(self, photo_urls: list[str], caption: str = None) -> list[dict]:
        if not photo_urls:
            raise Exception("Список 'photo_urls' пуст")

        content = []
        if caption:
            content.append({
                "type": "text", "text": caption
            })
        if len(photo_urls) == 1:
            content.append({
            "type": "image_url", "image_url": {
                "url": photo_urls[0]
            }
        })
        else:
            content += [{
                "type": "image_url",
                "image_url": {
                    "url": photo
                }
            } for photo in photo_urls]
        return content

    def create_messages(self, photo_urls: list[str], caption: str = None):
        content = self.create_content(photo_urls, caption)
        return super(ChatGPTVision, self).create_messages(content=content)