import argparse
import os
import re
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from constants import IMAGE_FILE_EXT_REGEX, SUPPORTED_IMAGE_EXT
from image_update import DockerImageContainerUpdateChecker
from process_image import process_image
from process_pdf import process_pdf
from process_xml import process_xml

DEFAULT_LANG = "en"
DEFAULT_MATHML_VERSION = "mathml-4"
DEFAULT_REGEX_TAG = "Table"
DEFAULT_OVERWRITE = False


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
                parser.add_argument("--key", type=str, help="PDFix license key")
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
            case "name":
                parser.add_argument("--name", type=str, help="PDFix license name")
            case "openai-key":
                parser.add_argument("--openai-key", type=str, required=True, help="OpenAI API key")
            case "output":
                parser.add_argument(
                    "--output", "-o", type=str, required=required_output, help=f"The output {file_type} file"
                )
            case "overwrite":
                parser.add_argument(
                    "--overwrite", type=bool, default=DEFAULT_OVERWRITE, help="Overwrite previous Alt text"
                )
            case "tags":
                parser.add_argument("--tags", type=str, default=DEFAULT_REGEX_TAG, help="Tag names to process")


def run_config_subcommand(args) -> None:
    get_pdfix_config(args.output)


def get_pdfix_config(path: str) -> None:
    """
    If Path is not provided, output content of config.
    If Path is provided, copy config to destination path.

    Args:
        path (string): Destination path for config.json file
    """
    config_path = os.path.join(Path(__file__).parent.absolute(), "../config.json")

    with open(config_path, "r", encoding="utf-8") as file:
        if path is None:
            print(file.read())
        else:
            with open(path, "w") as out:
                out.write(file.read())


def run_subcommand(args) -> None:
    process_cli(
        args.command,
        getattr(args, "name", None),
        getattr(args, "key", None),
        getattr(args, "openai_key", None),
        args.input,
        args.output,
        getattr(args, "lang", DEFAULT_LANG),
        getattr(args, "mathml_version", DEFAULT_MATHML_VERSION),
        getattr(args, "overwrite", DEFAULT_OVERWRITE),
        getattr(args, "tags", DEFAULT_REGEX_TAG),
    )


def process_cli(
    subcommand: str,
    license_name: Optional[str],
    license_key: Optional[str],
    openai_key: Optional[str],
    input: str,
    output: str,
    lang: str,
    mathml_version: str,
    overwrite: bool,
    regex_tag: str,
) -> None:
    """
    Processes a PDF or image file by extracting images,
    generating a response using OpenAI, and saving the result to an output file.

    Args:
        license_name (str): PDFix license name.
        license_key (str): PDFix license key.
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        input (str): Path to the input PDF or image file.
        output (str): Path to the output PDF or XML or TXT file.
        openai_key (str): OpenAI API key.
        lang (str): Language setting.
        mathml_version (str): MathML version.
        overwrite (bool): Whether to overwrite previous alternate text.
        regex_tag (str): Regular expression for matching tags that should be processed.
    """
    if not openai_key:
        raise ValueError(f"Invalid or missing arguments: --openai-key {openai_key}")

    if input.lower().endswith(".pdf") and output.lower().endswith(".pdf"):
        return process_pdf(
            subcommand, license_name, license_key, openai_key, input, output, lang, mathml_version, overwrite, regex_tag
        )
    elif re.search(IMAGE_FILE_EXT_REGEX, input, re.IGNORECASE) and output.lower().endswith((".xml", ".txt")):
        return process_image(subcommand, openai_key, input, output, lang, mathml_version)
    elif input.lower().endswith(".xml") and output.lower().endswith(".txt"):
        return process_xml(subcommand, openai_key, input, output, lang, mathml_version)
    else:
        input_extension = Path(input).suffix.lower()
        output_extension = Path(output).suffix.lower()
        exception_message = (
            f"Not supported file combination ({input_extension} -> {output_extension})"
            " Please run with --help to find out supported combinations."
        )
        raise Exception(exception_message)


def main():
    parser = argparse.ArgumentParser(description="PDF Accessibility with OpenAI")
    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # Generate table summary subparser
    supported_files = f"Supported file combinations: PDF -> PDF, Image -> TXT. Supported images: {SUPPORTED_IMAGE_EXT}."
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
            "tags",
            "lang",
            "overwrite",
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
            "tags",
            "lang",
            "overwrite",
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
            "tags",
            "mathml-version",
            "overwrite",
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
    except SystemExit as e:
        if e.code == 0:
            # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Please check the usage and try again.", file=sys.stderr)
        sys.exit(e.code)

    if hasattr(args, "func"):
        # Check for updates only when help is not checked
        update_checker = DockerImageContainerUpdateChecker()
        # Check it in separate thread not to be delayed when there is slow or no internet connection
        update_thread = threading.Thread(target=update_checker.check_for_image_updates)
        update_thread.start()

        # Measure the time it takes to make all requests
        start_time = time.time()  # Record the start time
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"\nProcessing started at: {current_time}")

        # Run subcommand
        try:
            args.func(args)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            end_time = time.time()  # Record the end time
            elapsed_time = end_time - start_time  # Calculate the elapsed time
            current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            print(f"\nProcessing finished at: {current_time}. Elapsed time: {elapsed_time:.2f} seconds")

            # Make sure to let update thread finish before exiting
            update_thread.join()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
