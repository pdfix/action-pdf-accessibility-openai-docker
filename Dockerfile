# Use the official Debian slim image as a base
FROM debian:bookworm-slim

# Install necessary dependencies
RUN apt-get update 
RUN apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/alt-text-openai/


# Create a virtual environment and install dependencies
ENV VIRTUAL_ENV=venv
RUN python3 -m venv venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY requirements.txt /usr/alt-text-openai/
RUN pip install --no-cache-dir -r requirements.txt 


# Copy the source code and requirements.txt into the container
COPY src/ /usr/alt-text-openai/src/
COPY config.json /usr/alt-text-openai/


ENTRYPOINT ["/usr/alt-text-openai/venv/bin/python3", "/usr/alt-text-openai/src/main.py"]
