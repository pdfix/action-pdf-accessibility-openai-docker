from ai import openai_prompt_with_xml


def process_xml(openai_key: str, input_path: str, output_path: str, model: str, lang: str, prompt: str) -> None:
    """
    Processes a XML file by using it as question for OpenAI, and saving the result to an output file.

    Args:
        openai_key (str): OpenAI API key.
        input_path (str): Path to the input XML file.
        output_path (str): Path to the output TXT file.
        model (str): OpenAI model.
        lang (str): Language for the response.
        prompt (str): Prompt for OpenAI.
    """

    with open(input_path, "r", encoding="utf-8") as file:
        xml_data = file.read()

    response = openai_prompt_with_xml(xml_data, openai_key, model, lang, prompt)
    output = response.message.content if response.message.content else ""

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(output)
