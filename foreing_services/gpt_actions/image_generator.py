from foreing_services.gpt_actions.main_ import ChatGPT4


class ChatGPTImageGenerator(ChatGPT4):
    model = "dall-e-3"

    async def generate_images(self, prompt, n=1):
        if len(prompt) > 1000:
            prompt = prompt[:1000]

        image = await self.client.images.generate(
            model=self.model,
            prompt=prompt,
            n=n,
            response_format="url"
        )
        return image.data