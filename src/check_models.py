import base64
import sys
from io import BytesIO
from typing import Any

from openai import OpenAI
from PIL import Image


def create_dummy_image_base64() -> str:
    image: Image.Image = Image.new("RGB", (1, 1), color=(255, 255, 255))
    buffer: BytesIO = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def test_model_image_support(client: OpenAI, dummy_image: str, model_id: str) -> bool:
    try:
        client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{dummy_image}"}},
                    ],
                }
            ],
            max_tokens=10,
        )
        return True
    except Exception:
        return False


if len(sys.argv) < 2:
    print("Usage: python check_models.py <your_openai_api_key>")
    sys.exit(1)

api_key: str = sys.argv[1]
client: OpenAI = OpenAI(api_key=api_key)
dummy_image: str = create_dummy_image_base64()

models: Any = client.models.list()
supported_models: list[str] = []

for model in models.data:
    if test_model_image_support(client, dummy_image, model.id):
        supported_models.append(model.id)
        print(f"✅ {model.id} supports image input")
    else:
        print(f"❌ {model.id} does NOT support image input")

print("Models that support image input:")
for model_id in supported_models:
    print(f"- {model_id}")
