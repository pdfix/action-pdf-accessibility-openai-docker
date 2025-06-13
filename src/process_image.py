import base64

from ai import openai_prompt_with_image
from page_renderer import get_image_bytes


def process_image(subcommand: str, openai_key: str, input: str, output: str, lang: str, mathml_version: str) -> None:
    """
    Generates OpenAI response from image into output file.

    Args:
        subcommand (str): Subcommand to determine the type of processing.
        openai_key (str): OpenAI API key.
        input (str): Path to the input JSON file.
        output (str): Path to the output JSON file.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.
    """
    data = get_image_bytes(input)

    if data is None:
        raise Exception(f"Failed to read image data from {input}")
    else:
        image_data: bytes = data

    base64_image = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
    response = openai_prompt_with_image(base64_image, openai_key, subcommand, lang, mathml_version)
    output = response.message.content if response.message.content else ""

    with open(output, "w", encoding="utf-8") as output_file:
        output_file.write(output)
