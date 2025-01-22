import argparse
import os
import shutil
import sys
from pathlib import Path
from pdf import process_pdf


def get_config(path: str) -> None:
    if path is None:
        with open(
            os.path.join(Path(__file__).parent.absolute(), "../config.json"),
            "r",
            encoding="utf-8",
        ) as f:
            print(f.read())
    else:
        src = os.path.join(Path(__file__).parent.absolute(), "../config.json")
        dst = path
        shutil.copyfile(src, dst)


def main():
    parser = argparse.ArgumentParser(
        description="PDF Accessibility with OpenAI",
    )
    subparsers = parser.add_subparsers(title="subparser")

    # Generate Alt Text subcommand
    parser_generate_config = subparsers.add_parser(
        "config",
        help="Save the default configuration file",
    )    

    parser_generate_alt_text = subparsers.add_parser(
        "generate-alt-text",
        help="Generate alternate text for images",
    )    
    parser_generate_table_summary = subparsers.add_parser(
        "generate-table-summary",
        help="Generate Table Summary",
    )    

    parser.add_argument("--name", type=str, default="", help="PDFix license name")
    parser.add_argument("--key", type=str, default="", help="PDFix license key")
    parser.add_argument("--openai-key", type=str, default="", help="OpenAI API key")

    parser.add_argument("-i", "--input", type=str, help="The input PDF file")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="The output file",
    )

    parser.add_argument(
        "--tags",
        type=str,
        required=False,
        default="",
        help="Regular expression defining the tag names tpo process",
    )
    parser.add_argument(
        "--overwrite",
        type=bool,
        default=False,
        help="Overwrite the existing value",
    )
    parser.add_argument(
        "--lang",
        type=str,
        required=False,
        default="en",
        help="The laguage of the alternate description and table summary",
    )

    # Print help if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    try:
        args = parser.parse_args()

    except SystemExit as e:
        if e.code == 0:  # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Error: " + str(e))
        sys.exit(1)

    if args.subparser == "config":
        get_config(args.output)
        sys.exit(0)

    # default arguments:
    if args.subparser == "generate-alt-text" and not args.tags:
        args.tags = "Figure|Formula"
    elif args.subparser == "generate-table-summary" and not args.tags:
        args.tags = "Table"

    # value checks:
    if not args.input:
        raise ValueError(f"Invalid or missing arguments --input {args.input}")
    if not args.output:
        raise ValueError(f"Invalid or missing arguments: --output {args.output}")
    if not args.openai_key:
        raise ValueError(
            f"Invalid or missing arguments: --openai-key {args.openai_key}"
        )

    if not os.path.isfile(args.input):
        sys.exit(f"Error: The input file '{args.input}' does not exist.")
        return

    if args.input.lower().endswith(".pdf") and args.output.lower().endswith(".pdf"):
        try:
            process_pdf(args)
        except Exception as e:
            sys.exit("Failed to run alternate description: {}".format(e))

    else:
        print("Input and output file must be PDF")


if __name__ == "__main__":
    main()
