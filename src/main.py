import argparse
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

from image_update import DockerImageContainerUpdateChecker
from process_json import process_json
from process_pdf import process_pdf

DEFAULT_LANG = "en"
DEFAULT_MATHML_VERSION = "mathml-4"
DEFAULT_REGEX_TAG = "Table"
DEFAULT_OVERWRITE = False


def set_arguments(
    parser: argparse.ArgumentParser, names: list, required_output: bool = True, file_type: str = "PDF or JSON"
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
    Processes a PDF or JSON file by extracting images,
    generating a response using OpenAI, and saving the result to an output file.

    Args:
        license_name (str): PDFix license name.
        license_key (str): PDFix license key.
        subcommand (str): The subcommand to run (e.g., "generate-alt-text", "generate-table-summary").
        input (str): Path to the input PDF or JSON file.
        output (str): Path to the output PDF or JSON file.
        openai_key (str): OpenAI API key.
        lang (str): Language setting.
        mathml_version (str): MathML version.
        overwrite (bool): Whether to overwrite previous alternate text.
        regex_tag (str): Regular expression for matching tags that should be processed.
    """
    if not openai_key:
        raise ValueError(f"Invalid or missing arguments: --openai-key {openai_key}")

    if input.lower().endswith(".pdf"):
        # process whole pdf document
        return process_pdf(
            subcommand, license_name, license_key, openai_key, input, output, lang, mathml_version, overwrite, regex_tag
        )
    elif input.lower().endswith(".json"):
        # process just json
        return process_json(subcommand, openai_key, input, output, lang, mathml_version)


def main():
    parser = argparse.ArgumentParser(description="PDF Accessibility with OpenAI")
    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # Generate table summary subcommand
    parser_generate_table_summary = subparsers.add_parser("generate-table-summary", help="Generate table summary")
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

    # Generate alternate text images subcommand
    parser_generate_alt_text = subparsers.add_parser("generate-alt-text", help="Generate alternate text for images")
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
    )
    parser_generate_alt_text.set_defaults(func=run_subcommand)

    # Generate MathML formula subcommand
    parser_generate_mathml = subparsers.add_parser("generate-mathml", help="Generate MathML for formulas")
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

    # Config subcommand
    parser_generate_config = subparsers.add_parser("config", help="Save the default configuration file")
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

    # Update of docker image checker
    update_checker = DockerImageContainerUpdateChecker()
    update_checker.check_for_image_updates()

    # Measure the time it takes to make all requests
    start_time = time.time()  # Record the start time

    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"\nProcessing started at: {current_time}")

    if hasattr(args, "func"):
        # Run subcommand
        try:
            args.func(args)
        except Exception as e:
            print(traceback.format_exc(), file=sys.stderr)
            print(f"Failed to run the program: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()

    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"\nProcessing finished at: {current_time}. Elapsed time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
