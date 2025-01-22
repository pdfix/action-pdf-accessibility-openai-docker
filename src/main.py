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
        description="Generate Alternate Text with OpenAI",
    )
    parser.add_argument(
        "subparser",
        choices=["config", "generate-alt-text", "generate-table-summary"],
        help="Sub-command to run",
    )

    parser.add_argument("--name", type=str, default="", help="Pdfix license name")
    parser.add_argument("--key", type=str, default="", help="Pdfix license key")
    parser.add_argument("--openai-key", type=str, default="", help="OpenAI API key")

    parser.add_subparsers(dest="subparser")

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
        required=True,
        default="Figure",
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

    else:
        if not args.input or not args.output or not args.openai_key:
            parser.error(
                "The following arguments are required:\
                -i/--input, -o/--output, --openai",
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
