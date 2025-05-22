import json

from ai import openai_prompt


def process_json(subcommand: str, openai_key: str, input: str, output: str, lang: str, mathml_version: str) -> None:
    """
    Processes a JSON file by extracting a base64-encoded image,
    generating a response using OpenAI, and saving the result to an output file.

    Parameters:
        subcommand (str): Subcommand to determine the type of processing.
        openai_key (str): OpenAI API key.
        input (str): Path to the input JSON file.
        output (str): Path to the output JSON file.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.

    The input JSON file should have the following structure:
    {
        "image": "<base64_encoded_image>"
    }

    The function performs the following steps:
    1. Reads the input JSON file.
    2. Extracts the base64-encoded image.
    3. Passes the image to `openai_propmpt()` to generate a response.
    4. Saves the response as a dictionary {"content": response} in the output JSON file.

    Example:
        process("input.json", "output.json", "your_openai_key", "generate-alt-text", "en", "2.0")
    """

    with open(input, "r", encoding="utf-8") as file:
        data = json.load(file)

    base64_image = data["image"]

    response = openai_prompt(base64_image, openai_key, subcommand, lang, mathml_version)

    output_data: dict[str, str] = {"content": str(response.message.content)}

    with open(output, "w", encoding="utf-8") as output_file:
        json.dump(output_data, output_file, indent=2, ensure_ascii=False)
