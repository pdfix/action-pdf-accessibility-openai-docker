import json
from pathlib import Path

from ai import openai_propmpt


def process_json(args):
    """
    Processes a JSON file by extracting a base64-encoded image,
    generating a response using OpenAI, and saving the result to an output file.

    Parameters:
        args (Namespace): An object with the following attributes:
            - input (str): Path to the input JSON file.
            - output (str): Path to the output JSON file.

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
        args = Namespace(input="input.json", output="output.json")
        process_json(args)
    """

    with open(args.input, "r", encoding="utf-8") as file:
        data = json.load(file)

    base64_image = data["image"]

    response = openai_propmpt(base64_image, args)

    output_data: dict[str, str] = {"content": response.message.content}

    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(output_data, output_file, indent=2, ensure_ascii=False)
