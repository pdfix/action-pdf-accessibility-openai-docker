import httpx
from openai import AuthenticationError, OpenAI
from openai.types.chat.chat_completion import ChatCompletion, Choice

from exceptions import OpenAIAuthenticationException
from prompt import PromptCreator


def openai_prompt_with_image(
    image: str, openai_key: str, model: str, lang: str, math_ml_version: str, prompt_creator: PromptCreator
) -> Choice:
    """
    Create a prompt for OpenAI, ask OpenAI, and wait for response.

    Args:
        image (str): Base64-encoded image string.
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.
        prompt_creator (PromptCreator): Prompt creator for OpenAI.

    Returns:
        First (most probable) response from OpenAI.
    """
    client: OpenAI = OpenAI(
        api_key=openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )

    formatted_prompt: str = prompt_creator.craft_prompt(lang, math_ml_version)

    try:
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
    except AuthenticationError as e:
        raise OpenAIAuthenticationException(e.message)

    # print(f" Responses: {len(response.choices)}")
    # for choice in response.choices:
    #     print(f"========== choice {choice.index + 1} =========")
    #     print(choice.message.to_json)
    #     print("==============================")

    # Test if ok
    client.close()

    return response.choices[0]


def openai_prompt_with_xml(
    xml_data: str, openai_key: str, model: str, lang: str, prompt_creator: PromptCreator
) -> Choice:
    """
    Create a prompt for OpenAI, ask OpenAI, and wait for response.

    Args:
        xml_data (str): String containing XML data (MathML representation of Formula).
        openai_key (str): OpenAI API key.
        model (str): OpenAI model.
        lang (str): Language for the response.
        prompt_creator (PromptCreator): Prompt creator for OpenAI.

    Returns:
        First (most probable) response from OpenAI.
    """
    client: OpenAI = OpenAI(
        api_key=openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )

    formatted_prompt: str = prompt_creator.craft_prompt(lang, "")

    try:
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
            max_tokens=2000,  # for XML each character is token (prevent running out of tokens)
            temperature=0,  # no randomness
        )
    except AuthenticationError as e:
        raise OpenAIAuthenticationException(e.message)

    # Test if ok
    client.close()

    return response.choices[0]
