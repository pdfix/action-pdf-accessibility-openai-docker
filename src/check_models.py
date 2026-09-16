#!/usr/bin/env python3
"""Probe which OpenAI models accept chat + image input."""

from __future__ import annotations

import base64
import os
import sys
from io import BytesIO

from openai import BadRequestError, NotFoundError, OpenAI, PermissionDeniedError
from PIL import Image

SKIP_PREFIXES: tuple[str, ...] = (
    "text-embedding",
    "whisper",
    "tts",
    "davinci",
    "babbage",
    "curie",
    "ada",
    "dall-e",
    "gpt-image",
    "sora",
    "omni-moderation",
    "computer-use",
)


def create_dummy_image_base64() -> str:
    image: Image.Image = Image.new("RGB", (8, 8), color=(255, 255, 255))
    buffer: BytesIO = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def main() -> None:
    api_key: str | None = os.environ.get("OPENAI_API_KEY")
    if not api_key and len(sys.argv) > 1:
        api_key = sys.argv[1]
    if not api_key:
        print("Usage: OPENAI_API_KEY=... python check_models.py")
        print("   or: python check_models.py <your_openai_api_key>")
        sys.exit(1)

    client: OpenAI = OpenAI(api_key=api_key)
    data_url: str = f"data:image/png;base64,{create_dummy_image_base64()}"

    model_ids: list[str] = sorted(
        m.id
        for m in client.models.list().data
        if not any(m.id.startswith(prefix) for prefix in SKIP_PREFIXES)
    )

    text_ok: list[str] = []
    vision_ok: list[str] = []

    for model_id in model_ids:
        try:
            client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "Say hi"}],
                max_completion_tokens=5,
            )
            text_ok.append(model_id)
        except (NotFoundError, PermissionDeniedError, BadRequestError) as exc:
            print(f"TEXT ❌ {model_id}: {type(exc).__name__}: {exc}")
            continue
        except Exception as exc:  # noqa: BLE001 — probe must keep going
            print(f"TEXT ❌ {model_id}: {type(exc).__name__}: {exc}")
            continue

        try:
            client.chat.completions.create(
                model=model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What color?"},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    }
                ],
                max_completion_tokens=5,
            )
            vision_ok.append(model_id)
            print(f"VISION ✅ {model_id}")
        except BadRequestError as exc:
            print(f"VISION ❌ {model_id}: {exc}")
        except Exception as exc:  # noqa: BLE001 — probe must keep going
            print(f"VISION ❌ {model_id}: {type(exc).__name__}: {exc}")

    print("\n=== chat OK ===")
    print("\n".join(f"- {model_id}" for model_id in text_ok) or "(none)")
    print("\n=== vision OK ===")
    print("\n".join(f"- {model_id}" for model_id in vision_ok) or "(none)")


if __name__ == "__main__":
    main()
