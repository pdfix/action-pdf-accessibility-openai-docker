import httpx
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion, Choice


def openai_prompt_with_image(
    image: str, openai_key: str, model: str, lang: str, math_ml_version: str, prompt: str
) -> Choice:
    """
    Create a prompt for OpenAI, ask OpenAI, and wait for response.

    Args:
        image (str): Base64-encoded image string.
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        prompt (str): Prompt for OpenAI.

    Returns:
        First (most probable) response from OpenAI.
    """
    client: OpenAI = OpenAI(
        api_key=openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )

    formatted_prompt: str = prompt.format(lang=lang, math_ml_version=math_ml_version)

    response: ChatCompletion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": formatted_prompt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"{image}",
                        },
                    },
                ],
            },
        ],
        max_tokens=100,
    )

    return response.choices[0]


def openai_prompt_with_xml(xml_data: str, openai_key: str, model: str, lang: str, prompt: str) -> Choice:
    """
    Create a prompt for OpenAI, ask OpenAI, and wait for response.

    Args:
        xml_data (str): String containing XML data (MathML representation of Formula).
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        prompt (str): Prompt for OpenAI.

    Returns:
        First (most probable) response from OpenAI.
    """
    client: OpenAI = OpenAI(
        api_key=openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )
    formatted_prompt: str = prompt.format(lang=lang, math_ml_version="")

    response: ChatCompletion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": formatted_prompt,
                    },
                    {"type": "text", "text": f"```xml\n{xml_data}\n```"},
                ],
            },
        ],
        max_tokens=100,
    )

    return response.choices[0]
