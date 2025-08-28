import base64
from typing import Optional

from openai.types.chat.chat_completion import Choice

from ai import openai_prompt_with_image
from page_renderer import get_image_bytes
from utils import add_mathml_metadata


def process_image(
    subcommand: str,
    openai_key: str,
    input_path: str,
    output_path: str,
    model: str,
    lang: str,
    mathml_version: str,
    prompt: str,
) -> None:
    """
    Generates OpenAI response from image into output file.

    Args:
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        openai_key (str): OpenAI API key.
        input_path (str): Path to the imagev file.
        output_path (str): Path to the output TXT or XML file.
        model (str): OpenAI model.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.
        prompt (str): Prompt for OpenAI.
    """
    data: Optional[bytes] = get_image_bytes(input_path)

    if data is None:
        raise Exception(f"Failed to read image data from {input_path}")
    else:
        image_data: bytes = data

    base64_image: str = f"data:image/jpeg;base64,{base64.b64encode(image_data).decode('utf-8')}"
    response: Choice = openai_prompt_with_image(base64_image, openai_key, model, lang, mathml_version, prompt)
    output: str = response.message.content if response.message.content else ""
    if subcommand == "generate-mathml":
        output = add_mathml_metadata(output)

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(output)
