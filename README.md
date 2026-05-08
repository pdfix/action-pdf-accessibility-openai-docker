# PDF Accessibility OpenAI

Utilizes OpenAI models (cloud-based) to describe images and formulas. Requires an OpenAI API key. For PDF output without watermarks, a **PDFix SDK** license is required.

## Table of Contents

- [PDF Accessibility OpenAI](#pdf-accessibility-openai)
  - [Getting started](#getting-started)
  - [Usage](#usage)
  - [Commands](#commands)
  - [Arguments](#arguments)
  - [Examples](#examples)
  - [Help \& support](#help--support)
  - [Licenses](#licenses)

## Getting started

You need Docker installed. The first run downloads the image and may take longer than later runs.

## Usage

Mount a folder into the container and run a subcommand:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/pdf-accessibility-openai:latest <command> [options]
```

## Commands

- `generate-alt-text`: Alternate text for images (PDF → PDF; image/XML → TXT)
- `generate-table-summary`: Table summaries (PDF → PDF; image → TXT)
- `generate-mathml`: MathML for formulas (PDF → PDF; image → TXT)

## Arguments

### Common (OpenAI commands)

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--openai-key` | yes | String (OpenAI API key) | OpenAI API key |
| `--input`, `-i` | yes | Path to `.pdf`, image, or `.xml` as supported by the command | Input file |
| `--output`, `-o` | yes | Path to output `.pdf`, `.txt`, or `.xml` as supported | Output file |
| `--model` | no | One of the supported model names (default: `gpt-4o-mini`) | OpenAI model |
| `--prompt` | no | Prompt text or path to a `.txt` file | Custom prompt |
| `--tags` | no | Regular expression string; if omitted, command defaults apply | Tag names to process |
| `--tags-count` | no | Integer (default **2**); PDF only | Surrounding tags in prompt |
| `--name` | no | String (PDFix account license name) | PDFix license name |
| `--key` | no | String (PDFix account license key) | PDFix license key |

### `generate-alt-text`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--lang` | no | Language code string (default: `en`) | Output language |
| `--overwrite` | no | Boolean string (default: `false`) | Overwrite existing Alt text |

Default when `--tags` is omitted: `Figure|Formula`.

### `generate-table-summary`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--lang` | no | Language code string (default: `en`) | Output language |
| `--overwrite` | no | Boolean string (default: `false`) | Overwrite existing summary |

Default when `--tags` is omitted: `Table`.

### `generate-mathml`

| Option | Required | Type / expected value | Description |
|---|:---:|---|---|
| `--mathml-version` | no | One of: `mathml-1`, `mathml-2`, `mathml-3`, `mathml-4` (default: `mathml-4`) | MathML version |
| `--overwrite` | no | Boolean string (default: `false`) | Overwrite existing output |

Default when `--tags` is omitted: `Formula`.

## Examples

Generate alternate text:

```bash
docker run --rm -v "$(pwd)":/data -w /data pdfix/pdf-accessibility-openai:latest \
  generate-alt-text --openai-key "${OPENAI_API_KEY}" \
  --name "${LICENSE_NAME}" --key "${LICENSE_KEY}" \
  --input /data/document.pdf --output /data/out.pdf \
  --tags "Figure|Formula" --lang en --overwrite true
```

## Help & support

For PDFix SDK licensing or issues, contact `support@pdfix.net`.

## Licenses

- [PDFix Terms](https://pdfix.net/terms)
- [OpenAI policies](https://openai.com/policies/)
