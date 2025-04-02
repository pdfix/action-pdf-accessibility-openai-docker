import argparse
import time
from datetime import datetime
import os, shutil, sys
from pathlib import Path
from process_pdf import process_pdf
from process_json import process_json


def get_config(args) -> None:
    with open(
        os.path.join(Path(__file__).parent.absolute(), "../config.json"),
        "r",
        encoding="utf-8",
    ) as f:
        if args.output is None:
                print(f.read())
        else:
            with open(args.output, "w") as out:
                out.write(f.read())

def process_cli(args) -> None:
    # value checks:
    if not args.input:
        raise ValueError(f"Invalid or missing arguments --input {args.input}")
    if not args.output:
        raise ValueError(f"Invalid or missing arguments: --output {args.output}")
    if not args.openai_key:
        raise ValueError(
            f"Invalid or missing arguments: --openai-key {args.openai_key}"
        )

    if args.input.lower().endswith(".pdf"):
        # process whole pdf document
        return process_pdf(args)
    elif args.input.lower().endswith(".json"):
        # process just json
        return process_json(args)



def setArgs(parser, names):
    for name in names:
        if name == "openai-key":
            parser.add_argument("--openai-key", type=str, required=True, help="OpenAI API key")
        elif name == "input":
            parser.add_argument("--input", "-i", type=str, required=True, help="The input PDF file")
        elif name == "output":
            parser.add_argument("--output", "-o", type=str, required=False, help="The output file")
        elif name == "tags":
            parser.add_argument("--tags", type=str, default="Table", help="Tag names to process")
        elif name == "lang":
            parser.add_argument("--lang", type=str, default="en", help="Language setting")
        elif name == "name":
            parser.add_argument("--name", type=str, help="License Name")
        elif name == "key":
            parser.add_argument("--key", type=str, help="License Key") 
        elif name == "overwrite":
            parser.add_argument("--overwrite", type=bool, default=False, help="Overwrite previous Alt text") 
        elif name == "mathml-version":
            parser.add_argument("--mathml-version", type=str, choices=["mathml-1", "mathml-2", "mathml-3", "mathml-4"], default="mathml-4", help="MathML version")
    return parser

def main():
    try:
        parser = argparse.ArgumentParser(description="PDF Accessibility with OpenAI")
        subparsers = parser.add_subparsers(
            title="Commands", dest="command", required=True
        )

        # `generate-table-summary`
        parser_generate_table_summary = subparsers.add_parser(
            "generate-table-summary", help="Generate table summary"            
        )
        setArgs(parser_generate_table_summary, ["openai-key", "input", "output", "tags", "lang", "name", "key", "overwrite"])
        parser_generate_table_summary.set_defaults(func=process_cli)

        # `generate-alt-text`
        parser_generate_alt_text = subparsers.add_parser(
            "generate-alt-text", help="Generate alternate text for images"
        )
        setArgs(parser_generate_alt_text, ["openai-key", "input", "output", "tags", "lang", "name", "key", "overwrite"])
        parser_generate_alt_text.set_defaults(func=process_cli)

        # `generate-mathml`
        parser_generate_mathml = subparsers.add_parser(
            "generate-mathml", help="Generate MathML for formulas"
        )
        setArgs(parser_generate_mathml, ["openai-key", "input", "output", "tags", "mathml-version", "name", "key", "overwrite"])  
        parser_generate_mathml.set_defaults(func=process_cli)

        # `config` (does not require `input` or `output`)
        parser_generate_config = subparsers.add_parser(
            "config", help="Save the default configuration file"
        )
        setArgs(parser_generate_config, ["output"])
        parser_generate_config.set_defaults(func=get_config)

        # Parsovanie argumentov
        args = parser.parse_args()

        # Measure the time it takes to make all requests
        start_time = time.time()  # Record the start time

        dayTyme = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"\nProcessing started at: {dayTyme}")
        
        # Spustenie priradenej funkcie
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
