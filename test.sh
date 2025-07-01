#!/bin/bash

# This is local docker test during build and push action.

# Colors for output into console
GREEN='\033[0;32m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print info messages
info() { echo -e "${PURPLE}$1${NC}"; }

# Function to print success messages
success() { echo -e "${GREEN}$1${NC}"; }

# Function to print error messages
error() { echo -e "${RED}ERROR: $1${NC}"; }

# Check if the required arguments are provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <OPENAI_API_KEY>"
    exit 1
fi

# init
pushd "$(dirname $0)" > /dev/null

EXIT_STATUS=0
DOCKER_IMAGE="pdf-accessibility-openai:test"
PLATFORM="--platform linux/amd64"
TEMPORARY_DIRECTORY=".test"
OPENAI_API_KEY=$1

info "Building docker image..."
docker build $PLATFORM --rm -t $DOCKER_IMAGE .

if [ -d "$(pwd)/$TEMPORARY_DIRECTORY" ]; then
    rm -rf $(pwd)/$TEMPORARY_DIRECTORY
fi
mkdir -p $(pwd)/$TEMPORARY_DIRECTORY

info "List files in /usr/alt-text-openai"
docker run --rm $PLATFORM -v $(pwd):/data -w /data --entrypoint ls $DOCKER_IMAGE /usr/alt-text-openai/

info "Test #01: Show help"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE --help > /dev/null
if [ $? -eq 0 ]; then
    success "passed"
else
    error "Failed to run \"--help\" command"
    EXIT_STATUS=1
fi

info "Test #02: Extract config"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE config -o $TEMPORARY_DIRECTORY/config.json > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/config.json" ]; then
    success "passed"
else
    error "config.json not saved"
    EXIT_STATUS=1
fi

info "Test #03: Run gen alt text pdf->pdf"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text --openai-key $OPENAI_API_KEY -i example/air_quality-tagged.pdf -o $TEMPORARY_DIRECTORY/air_quality-tagged-alt-text.pdf --overwrite true > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/air_quality-tagged-alt-text.pdf" ]; then
    success "passed"
else
    error "gen alt text pdf->pdf failed on example/air_quality-tagged.pdf"
    EXIT_STATUS=1
fi

info "Test #04: Run gen alt text img->txt"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text --openai-key $OPENAI_API_KEY -i example/image_example.jpg -o $TEMPORARY_DIRECTORY/image_example.txt > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/image_example.txt" ]; then
    success "passed"
else
    error "gen alt text img->txt failed on example/image_example.jpg"
    EXIT_STATUS=1
fi

info "Test #05: Run mathml pdf->pdf"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-mathml --openai-key $OPENAI_API_KEY -i example/air_quality-tagged.pdf -o $TEMPORARY_DIRECTORY/air_quality-mathml.pdf --overwrite true > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/air_quality-mathml.pdf" ]; then
    success "passed"
else
    error "mathml pdf->pdf failed on $TEMPORARY_DIRECTORY/air_quality-tagged.pdf"
    EXIT_STATUS=1
fi

info "Test #06: Run mathml img->xml"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-mathml --openai-key $OPENAI_API_KEY -i example/formula_example.jpg -o $TEMPORARY_DIRECTORY/formula_example.xml > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/formula_example.xml" ]; then
    success "passed"
else
    error "mathml img->xml failed on example/formula_example.jpg"
    EXIT_STATUS=1
fi

info "Test #07: Run gen alt text xml->txt"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-alt-text --openai-key $OPENAI_API_KEY -i $TEMPORARY_DIRECTORY/formula_example.xml -o $TEMPORARY_DIRECTORY/formula_example.txt > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/formula_example.txt" ]; then
    success "passed"
else
    error "gen alt text xml->txt failed on example/formula_example.xml"
    EXIT_STATUS=1
fi

info "Test #08: Run table summary pdf->pdf"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-table-summary --openai-key $OPENAI_API_KEY -i example/food_fact_sheet-tagged.pdf -o $TEMPORARY_DIRECTORY/food_fact_sheet-tagged-table.pdf --overwrite true  > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/food_fact_sheet-tagged-table.pdf" ]; then
    success "passed"
else
    error "table summary pdf->pdf failed on example/food_fact_sheet-tagged.pdf"
    EXIT_STATUS=1
fi

info "Test #09: Run table summary img->txt"
docker run --rm $PLATFORM -v $(pwd):/data -w /data $DOCKER_IMAGE generate-table-summary --openai-key $OPENAI_API_KEY -i example/table_example.jpg -o $TEMPORARY_DIRECTORY/table_example.txt  > /dev/null
if [ -f "$(pwd)/$TEMPORARY_DIRECTORY/table_example.txt" ]; then
    success "passed"
else
    error "table summary img->txt failed on example/table_example.jpg"
    EXIT_STATUS=1
fi

info "Cleaning up temporary files from tests"
rm -f $TEMPORARY_DIRECTORY/config.json
rm -f $TEMPORARY_DIRECTORY/air_quality-tagged-alt-text.pdf
rm -f $TEMPORARY_DIRECTORY/image_example.txt
rm -f $TEMPORARY_DIRECTORY/air_quality-mathml.pdf
rm -f $TEMPORARY_DIRECTORY/formula_example.xml
rm -f $TEMPORARY_DIRECTORY/formula_example.txt
rm -f $TEMPORARY_DIRECTORY/food_fact_sheet-tagged-table.pdf
rm -f $TEMPORARY_DIRECTORY/table_example.txt
rmdir $(pwd)/$TEMPORARY_DIRECTORY

info "Removing testing docker image"
docker rmi $DOCKER_IMAGE

popd > /dev/null

if [ $EXIT_STATUS -eq 1 ]; then
    error "One or more tests failed."
    exit 1
else
    success "All tests passed."
    exit 0
fi
