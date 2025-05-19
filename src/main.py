import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from image_update import check_for_image_updates
from process_json import process_json
from process_pdf import process_pdf


def get_config(args) -> None:
    config_path = os.path.join(Path(__file__).parent.absolute(), "../config.json")

    with open(config_path, "r", encoding="utf-8") as file:
        if args.output is None:
            print(file.read())
        else:
            with open(args.output, "w") as out:
                out.write(file.read())


def process_cli(args) -> None:
    # value checks:
    if not args.input:
        raise ValueError(f"Invalid or missing arguments --input {args.input}")
    if not args.output:
        raise ValueError(f"Invalid or missing arguments: --output {args.output}")
    if not args.openai_key:
        raise ValueError(f"Invalid or missing arguments: --openai-key {args.openai_key}")

    if args.input.lower().endswith(".pdf"):
        # process whole pdf document
        return process_pdf(args)
    elif args.input.lower().endswith(".json"):
        # process just json
        return process_json(args)


def set_arguments(
    parser: argparse.ArgumentParser, names: list, required_output: bool = True, file_type: str = "PDF or JSON"
) -> None:
    for name in names:
        match name:
            case "input":
                parser.add_argument("--input", "-i", type=str, required=True, help=f"The input {file_type} file")
            case "key":
                parser.add_argument("--key", type=str, help="PDFix license key")
            case "lang":
                parser.add_argument("--lang", type=str, default="en", help="Language setting")
            case "mathml-version":
                parser.add_argument(
                    "--mathml-version",
                    type=str,
                    choices=["mathml-1", "mathml-2", "mathml-3", "mathml-4"],
                    default="mathml-4",
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
                parser.add_argument("--overwrite", type=bool, default=False, help="Overwrite previous Alt text")
            case "tags":
                parser.add_argument("--tags", type=str, default="Table", help="Tag names to process")


def main():
    try:
        parser = argparse.ArgumentParser(description="PDF Accessibility with OpenAI")
        subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

        # `generate-table-summary`
        parser_generate_table_summary = subparsers.add_parser("generate-table-summary", help="Generate table summary")
        set_arguments(
            parser_generate_table_summary,
            [
                "name",
                "key",
                "input",
                "output",
                "openai-key",
                "tags",
                "lang",
                "overwrite",
            ],
        )
        parser_generate_table_summary.set_defaults(func=process_cli)

        # `generate-alt-text`
        parser_generate_alt_text = subparsers.add_parser("generate-alt-text", help="Generate alternate text for images")
        set_arguments(
            parser_generate_alt_text,
            [
                "name",
                "key",
                "input",
                "output",
                "openai-key",
                "tags",
                "lang",
                "overwrite",
            ],
        )
        parser_generate_alt_text.set_defaults(func=process_cli)

        # `generate-mathml`
        parser_generate_mathml = subparsers.add_parser("generate-mathml", help="Generate MathML for formulas")
        set_arguments(
            parser_generate_mathml,
            [
                "input",
                "output",
                "name",
                "key",
                "openai-key",
                "tags",
                "mathml-version",
                "overwrite",
            ],
        )
        parser_generate_mathml.set_defaults(func=process_cli)

        # `config` (does not require `input` or `output`)
        parser_generate_config = subparsers.add_parser("config", help="Save the default configuration file")
        set_arguments(parser_generate_config, ["output"], False, "JSON")
        parser_generate_config.set_defaults(func=get_config)

        # Parse arguments
        args = parser.parse_args()

        check_for_image_updates()

        # Measure the time it takes to make all requests
        start_time = time.time()  # Record the start time

        dayTyme = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"\nProcessing started at: {dayTyme}")

        # Run assigned function
        if hasattr(args, "func"):
            args.func(args)
        else:
            parser.print_help()

        end_time = time.time()  # Record the end time
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        print(f"\nProcessing finished at: {dayTyme}. Elapsed time: {elapsed_time:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
