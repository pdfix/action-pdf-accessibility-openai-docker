# PDF Accessibility with OpenAI

A Docker image that enhances the accessibility of PDF documents using OpenAI and PDFix SDK. Automatically generates alternate text for images and formulas, summarizes tables, and produces MathML associate files for formulas.

## Table of Contents

- [PDF Accessibility with OpenAI](#pdf-accessibility-with-openai)
  - [Table of Contents](#table-of-contents)
  - [Available Actions](#available-actions)
    - [Generate Alternate Text for images](#generate-alternate-text-for-images)
    - [Generate Table Summary](#generate-table-summary)
    - [Generate MathML Associated Files for Formulas](#generate-mathml-associated-files-for-formulas)
  - [Getting Started](#getting-started)
  - [Run using Command Line Interface](#run-using-command-line-interface)
  - [Export the Configuration File for Integration](#export-the-configuration-file-for-integration)
  - [License \& libraries used](#license--libraries-used)
  - [Help \& Support](#help--support)
  
## Available Actions
- Generate Alternate Text for images
- Generate Table Summary
- Generate MathML Associated Files for Formulas

### Generate Alternate Text for images

Automatically generates alternate text for Figure and Formula tags using OpenAI, embedding it into each tag’s Alt attribute.

### Generate Table Summary

Automatically generates table summaries for Table tags using OpenAI, inserting them into each tag’s Summary attribute.

### Generate MathML Associated Files for Formulas

Automatically generates MathML for Formula tags using OpenAI, attaching it as an associated file to each tag.


```bash
PDF Accessibility with OpenAI

commands:
    generate-table-summary
                        Generate table summary. Supported file combinations: PDF -> PDF, Image -> TXT. Supported images: .jpg .jpeg .png .bmp.
    generate-alt-text   Generate alternate text for images. Supported file combinations: PDF -> PDF, Image or XML -> TXT. Supported images: .jpg .jpeg .png .bmp.
    generate-mathml     Generate MathML for formulas. Supported file combinations: PDF -> PDF, Image -> TXT. Supported images: .jpg .jpeg .png .bmp.
    config              Save the default configuration file.

common options:
  -h, --help                show this help message and exit
  --openai-key OPENAI_KEY   OpenAI API key
  --input INPUT             The input PDF or image file
  --output OUTPUT           The output file
  --tags TAGS               Regular expression defining the tag names tpo process
  --name NAME               PDFix license name
  --key KEY                 PDFix license key

generate-alt-text, generate-table-summary:
  --lang LANG               The laguage of the alternate description and table summary
  --overwrite OVERWRITE     Overwrite the existing value

generate-mathml:
  --mathml-version          MathML version
      {mathml-1,mathml-2,mathml-3,mathml-4}
```

## Getting Started

To use this Docker application, you'll need to have Docker installed on your system. If Docker is not installed, please follow the instructions on the [official Docker website](https://docs.docker.com/get-docker/) to install it.

## Run using Command Line Interface

To run the docker container as CLI, you should share the folder containing the PDF for processing using the `-i` parameter. In this example, the current folder is used.

```bash 
docker run -v $(pwd):/data/ -w /data pdfix/pdf-accessibility-openai:latest generate-alt-text --input document.pdf --output out.pdf --tags "Figure|Formula" --openai-key <api_key> --lang English --overwrite true
```

To run With a PDFix License add these arguments.

```bash
--name ${LICENSE_NAME} --key ${LICENSE_KEY}
```
Contact support for more infomation.

First run will pull the docker image, which may take some time. Make your own image for more advanced use.

For more detailed information about the available command-line arguments, you can run the following command:

```bash
docker run --rm pdfix/pdf-accessibility-openai:latest --help
```

## Export the Configuration File for Integration
To export the configuration JSON file, use the following command:

```bash
docker run -v $(pwd):/data -w /data --rm pdfix/pdf-accessibility-openai:latest config --output config.json
```

## License & libraries used
- PDFix SDK - https://pdfix.net/terms
- OpenAI API - https://openai.com/policies/

Trial version of the PDFix SDK may apply a watermark on the page and redact random parts of the PDF including the scanned image in background. Contact us to get an evaluation or production license.

## Help & Support
To obtain a PDFix SDK license or report an issue please contact us at support@pdfix.net.
For more information visit https://pdfix.net
