from ai import openai_prompt_with_xml


def process_xml(
    subcommand: str, openai_key: str, input_path: str, output_path: str, lang: str, mathml_version: str
) -> None:
    """
    Processes a XML file by using it as question for OpenAI, and saving the result to an output file.

    Args:
        subcommand (str): Subcommand to determine the type of processing.
        openai_key (str): OpenAI API key.
        input_path (str): Path to the input XML file.
        output_path (str): Path to the output TXT file.
        lang (str): Language for the response.
        mathml_version (str): MathML version for the response.
    """

    with open(input_path, "r", encoding="utf-8") as file:
        xml_data = file.read()

    response = openai_prompt_with_xml(xml_data, openai_key, subcommand, lang, mathml_version)
    output = response.message.content if response.message.content else ""

    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(output)
