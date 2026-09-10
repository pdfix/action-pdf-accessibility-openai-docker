import argparse
import json
import logging
import re
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from constants import CONFIG_FILE, IMAGE_FILE_EXT_REGEX, SUPPORTED_IMAGE_EXT
from exceptions import (
    EC_ARG_GENERAL,
    MESSAGE_ARG_GENERAL,
    ArgumentException,
    ArgumentInputOutputNotAllowedException,
    ArgumentOpenAIKeyException,
    ExpectedException,
    InvalidRegexOrTemplateException,
)
from image_update import DockerImageContainerUpdateChecker
from logger import get_logger, set_console_level
from params_parser import ParamsParser
from process_image import process_image
from process_pdf import process_pdf
from process_xml import process_xml
from prompt import PromptCreator

DEFAULT_LANG: str = "en"
DEFAULT_MATHML_VERSION: str = "mathml-4"
DEFAULT_OVERWRITE: bool = False
DEFAULT_TAGS_COUNT: int = 2
DEFAULT_VERBOSE: bool = False
DEFAULT_TAGS_ALT_TEXT: str = "Figure|Formula"
DEFAULT_TAGS_TABLE: str = "Table"
DEFAULT_TAGS_MATHML: str = "Formula"

logger: logging.Logger = get_logger()


def str2bool(value: Any) -> bool:
    """
    Helper function to convert argument to boolean.

    Args:
        value (Any): The value to convert to boolean.

    Returns:
        Parsed argument as boolean.
    """
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "1"):
        return True
    elif value.lower() in ("no", "false", "f", "0"):
        return False
    else:
        raise ArgumentException(f"{MESSAGE_ARG_GENERAL} Boolean value expected.")


def set_arguments(
    parser: argparse.ArgumentParser, names: list, required_output: bool = True, file_type: str = "PDF or Image"
) -> None:
    """
    Set arguments for the parser based on the provided names and options.

    Args:
        parser (argparse.ArgumentParser): The argument parser to set arguments for.
        names (list): List of argument names to set.
        required_output (bool): Whether the output argument is required. Defaults to True.
        file_type (str): The type of file being processed. Defaults to "PDF or JSON".
    """
    for name in names:
        match name:
            case "input":
                parser.add_argument("--input", "-i", type=str, required=True, help=f"The input {file_type} file")
            case "key":
                parser.add_argument("--key", type=str, default="", nargs="?", help="PDFix license key")
            case "lang":
                parser.add_argument("--lang", type=str, default=DEFAULT_LANG, help="Language setting")
            case "mathml-version":
                parser.add_argument(
                    "--mathml-version",
                    type=str,
                    choices=["mathml-1", "mathml-2", "mathml-3", "mathml-4"],
                    default=DEFAULT_MATHML_VERSION,
                    help="MathML version",
                )
            case "model":
                parser.add_argument(
                    "--model",
                    type=str,
                    choices=[
                        "gpt-4-turbo",
                        "gpt-4o",
                        "gpt-4o-mini",
                        "chatgpt-4o-latest",
                        "gpt-4.1",
                        "gpt-4.1-mini",
                        "gpt-4.1-nano",
                        "gpt-5-chat-latest",
                    ],
                    default="gpt-4o-mini",
                    help="OpenAI model to use for processing",
                )
            case "name":
                parser.add_argument("--name", type=str, default="", nargs="?", help="PDFix license name")
            case "openai-key":
                parser.add_argument("--openai-key", type=str, required=True, help="OpenAI API key")
            case "output":
                parser.add_argument(
                    "--output", "-o", type=str, required=required_output, help=f"The output {file_type} file"
                )
            case "overwrite":
                parser.add_argument(
                    "--overwrite", type=str2bool, default=DEFAULT_OVERWRITE, help="Overwrite previous Alt text"
                )
            case "params":
                parser.add_argument(
                    "--params",
                    type=str,
                    required=False,
                    help="Path to JSON file with tag filter parameters (required for PDF → PDF).",
                )
            case "prompt":
                parser.add_argument(
                    "--prompt",
                    type=str,
                    default="",
                    help="Prompt used for generating response. If not provided, default prompt will be used.",
                )
            case "tags-count":
                parser.add_argument(
                    "--tags-count",
                    type=int,
                    default=DEFAULT_TAGS_COUNT,
                    help="How many surrounding tags information is used in prompt (works only with pdf files).",
                )
            case "verbose":
                parser.add_argument("-v", "--verbose", type=str2bool, default=DEFAULT_VERBOSE, help="Verbose output")


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path: Path = Path(__file__).parent.parent.joinpath(CONFIG_FILE).resolve()

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def default_tags_for_command(command: str) -> str:
    """
    Return the default tag regex for a command when --params is omitted.

    Args:
        command (str): Subcommand name.

    Returns:
        Default ECMAScript regular expression for tag names.
    """
    if command == "generate-table-summary":
        return DEFAULT_TAGS_TABLE
    if command == "generate-mathml":
        return DEFAULT_TAGS_MATHML
    return DEFAULT_TAGS_ALT_TEXT


def resolve_regex_template(args) -> str | Path | dict:
    """
    Resolve tag filter from --params (regex or template) or command defaults.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Either a regex string, a template dict, or (via caller) a Path to template JSON.
    """
    params_path: Optional[str] = getattr(args, "params", None)
    if not params_path:
        return default_tags_for_command(args.command)

    params_parser = ParamsParser(params_path)
    params_parser.parse()
    tag_names: Any = params_parser.params.get("tag_names")
    if isinstance(tag_names, str):
        return tag_names
    if isinstance(tag_names, dict):
        return tag_names
    raise InvalidRegexOrTemplateException()


def run_subcommand(args) -> None:
    # Print everything into console
    if args.verbose:
        set_console_level(logging.DEBUG)

    tag_filter: str | Path | dict = resolve_regex_template(args)
    if isinstance(tag_filter, dict):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json") as template_file:
            with open(template_file.name, "w", encoding="utf-8") as template_file_write:
                json.dump(tag_filter, template_file_write)
            process_cli_from_args(args, Path(template_file.name))
    else:
        process_cli_from_args(args, tag_filter)


def process_cli_from_args(args, regex_template: str | Path) -> None:
    """
    Run process_cli using parsed argparse namespace and resolved tag filter.

    Args:
        args: Parsed CLI arguments.
        regex_template (str | Path): Regex or path to template JSON.
    """
    process_cli(
        args.command,
        getattr(args, "name", None),
        getattr(args, "key", None),
        getattr(args, "openai_key", None),
        args.input,
        args.output,
        args.model,
        getattr(args, "lang", DEFAULT_LANG),
        getattr(args, "mathml_version", DEFAULT_MATHML_VERSION),
        getattr(args, "overwrite", DEFAULT_OVERWRITE),
        regex_template,
        args.prompt,
        getattr(args, "tags_count", DEFAULT_TAGS_COUNT),
    )


def process_cli(
    subcommand: str,
    license_name: Optional[str],
    license_key: Optional[str],
    openai_key: Optional[str],
    input: str,
    output: str,
    model: str,
    lang: str,
    mathml_version: str,
    overwrite: bool,
    regex_template: str | Path,
    prompt: str,
    surround_tags_count: int,
) -> None:
    """
    Processes a PDF or image file by extracting images,
    generating a response using OpenAI, and saving the result to an output file.

    Args:
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        license_name (str): PDFix license name.
        license_key (str): PDFix license key.
        openai_key (str): OpenAI API key.
        input (str): Path to the input PDF or image file.
        output (str): Path to the output PDF or XML or TXT file.
        model (str): OpenAI model.
        lang (str): Language setting.
        mathml_version (str): MathML version.
        overwrite (bool): Whether to overwrite previous alternate text.
        regex_template (str | Path): Regex or path to template JSON for matching tags.
        prompt (str): Prompt used for generating response.
        surround_tags_count (int): Number of tags included into prompt.
    """
    if not openai_key:
        raise ArgumentOpenAIKeyException()

    is_xml_input: bool = input.lower().endswith(".xml")
    prompt_creator: PromptCreator = PromptCreator(prompt, subcommand, is_xml_input)

    if input.lower().endswith(".pdf") and output.lower().endswith(".pdf"):
        return process_pdf(
            subcommand,
            license_name,
            license_key,
            openai_key,
            input,
            output,
            model,
            lang,
            mathml_version,
            overwrite,
            regex_template,
            prompt_creator,
            surround_tags_count,
        )
    elif re.search(IMAGE_FILE_EXT_REGEX, input, re.IGNORECASE) and output.lower().endswith((".xml", ".txt")):
        return process_image(subcommand, openai_key, input, output, model, lang, mathml_version, prompt_creator)
    elif is_xml_input and output.lower().endswith(".txt"):
        return process_xml(openai_key, input, output, model, lang, prompt_creator)
    else:
        input_extension: str = Path(input).suffix.lower()
        output_extension: str = Path(output).suffix.lower()
        combination: str = f"{input_extension} -> {output_extension})"
        raise ArgumentInputOutputNotAllowedException(combination)


def main():
    parser = argparse.ArgumentParser(description="PDF Accessibility with OpenAI")
    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # Generate table summary subparser
    supported_files = "Supported file combinations: PDF -> PDF, Image -> TXT."
    supported_files += f" Supported images: {SUPPORTED_IMAGE_EXT}."
    parser_generate_table_summary = subparsers.add_parser(
        "generate-table-summary", help=f"Generate table summary. {supported_files}"
    )
    set_arguments(
        parser_generate_table_summary,
        [
            "name",
            "key",
            "openai-key",
            "input",
            "output",
            "model",
            "lang",
            "params",
            "overwrite",
            "prompt",
            "tags-count",
            "verbose",
        ],
    )
    parser_generate_table_summary.set_defaults(func=run_subcommand)

    # Generate alternate text images subparser
    supported_files = "Supported file combinations: PDF -> PDF, Image or XML -> TXT."
    supported_files += f" Supported images: {SUPPORTED_IMAGE_EXT}."
    parser_generate_alt_text = subparsers.add_parser(
        "generate-alt-text", help=f"Generate alternate text for images. {supported_files}"
    )
    set_arguments(
        parser_generate_alt_text,
        [
            "name",
            "key",
            "openai-key",
            "input",
            "output",
            "model",
            "lang",
            "params",
            "overwrite",
            "prompt",
            "tags-count",
            "verbose",
        ],
        True,
        "PDF or image or XML",
    )
    parser_generate_alt_text.set_defaults(func=run_subcommand)

    # Generate MathML formula subparser
    supported_files = f"Supported file combinations: PDF -> PDF, Image -> TXT. Supported images: {SUPPORTED_IMAGE_EXT}."
    parser_generate_mathml = subparsers.add_parser(
        "generate-mathml", help=f"Generate MathML for formulas. {supported_files}"
    )
    set_arguments(
        parser_generate_mathml,
        [
            "name",
            "key",
            "openai-key",
            "input",
            "output",
            "model",
            "params",
            "mathml-version",
            "overwrite",
            "prompt",
            "tags-count",
            "verbose",
        ],
    )
    parser_generate_mathml.set_defaults(func=run_subcommand)

    # Config subparser
    parser_generate_config = subparsers.add_parser("config", help="Save the default configuration file.")
    set_arguments(parser_generate_config, ["output"], False, "JSON")
    parser_generate_config.set_defaults(func=run_config_subcommand)

    # Parse arguments
    try:
        args = parser.parse_args()
    except ExpectedException as e:
        logger.exception(e.message)
        sys.exit(e.error_code)
    except SystemExit as e:
        if e.code != 0:
            logger.exception(MESSAGE_ARG_GENERAL)
            sys.exit(EC_ARG_GENERAL)
        # This happens when --help is used, exit gracefully
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Failed to run the program:{e}")
        sys.exit(1)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Measure the time it takes to make all requests
        start_time = time.time()  # Record the start time
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"\nProcessing started at: {current_time}")

        # Run subcommand
        try:
            args.func(args)
        except ExpectedException as e:
            logger.exception(e.message)
            sys.exit(e.error_code)
        except Exception as e:
            logger.exception(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            end_time = time.time()  # Record the end time
            elapsed_time = end_time - start_time  # Calculate the elapsed time
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            logger.info(f"\nProcessing finished at: {current_time}. Elapsed time: {elapsed_time:.2f} seconds")

            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
