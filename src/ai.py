import httpx
from openai import OpenAI
from openai.types.chat.chat_completion import Choice


def openai_prompt(image: str, openai_key: str, subcommand: str, lang: str, math_ml_version: str) -> Choice:
    """
    Create a prompt for OpenAI, ask OpenAI, and wait for response.

    Args:
        image (str): Base64-encoded image string.
        openai_key (str): OpenAI API key.
        subcommand (str): Subcommand to determine the type of processing.
        lang (str): Language for the response.
        math_ml_version (str): MathML version for the response.

    Returns:
        First (most probable) response from OpenAI.
    """
    client = OpenAI(
        api_key=openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )

    if subcommand == "generate-alt-text":
        # image alternate text prompt
        prompt = f"Provide only the alt text for the image in {lang} language,"
        prompt += " describing the content in a concise, clear, and meaningful way."
        prompt += " Focus on the essential details, conveying the purpose of the image for screen readers."
        prompt += " Include relevant information about the image's context, objects, people,"
        prompt += " and any key actions or emotions, while keeping the description brief but informative."
    elif subcommand == "generate-table-summary":
        # table summary text prompt
        prompt = f"Describe the table in {lang} language concisely without repeating its data."
        prompt += " Keep the response brief and focus on structure, and content."
        prompt += " Provide only the response without any additional explanation or context."
    elif subcommand == "generate-mathml":
        # formula mathml text prompt
        prompt = f"Extract only the plain xml MathML {math_ml_version}"
        prompt += " representation of the mathematical expression from the provided image,"
        prompt += " without any additional explanation, description, or markdown code formatting."
    else:
        raise ValueError(f"Unknown subparser value {subcommand}")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
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
