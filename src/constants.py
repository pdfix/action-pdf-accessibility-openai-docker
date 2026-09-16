CONFIG_FILE: str = "config.json"
DOCKER_NAMESPACE: str = "pdfix"
DOCKER_REPOSITORY: str = "pdf-accessibility-openai"
DOCKER_IMAGE: str = f"{DOCKER_NAMESPACE}/{DOCKER_REPOSITORY}"
IMAGE_FILE_EXT_REGEX: str = r"\.(jpg|jpeg|png|bmp)$"
PROGRESS_FIRST_STEP: int = 50  # Initialize (open document, find out elements to process, etc.)
PROGRESS_SECOND_STEP: int = 900  # Run AI heavy workload (+ rendering)
PROGRESS_THIRD_STEP: int = 50  # Save document
SUPPORTED_IMAGE_EXT: str = ".jpg .jpeg .png .bmp"

# Allowed OpenAI vision/chat models (CLI + Desktop config dropdown).
DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"
OPENAI_MODELS: tuple[str, ...] = (
    "chat-latest",
    "gpt-4-turbo",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-search-api",
    "gpt-5.2",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    "o1",
    "o3",
    "o3-mini",
    "o4-mini",
)
