
def create_prompt_for_gen_model(is_male: bool, prompt: str | None = None):
    base_prompt = "A full-length {gender} poses for a photo. The whole body should be visible" \
                  "{additional_prompt}"
    base_prompt_kwargs = {}

    if is_male:
        base_prompt_kwargs.update(gender="man")
    else:
        base_prompt_kwargs.update(gender="woman")

    if prompt:
        base_prompt_kwargs.update(additional_prompt=". " + prompt)
    else:
        base_prompt_kwargs.update(additional_prompt="")
    return base_prompt.format(**base_prompt_kwargs)