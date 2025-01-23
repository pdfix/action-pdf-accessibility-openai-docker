import httpx
from openai import OpenAI


def openai_propmpt(img: str, args):
    client = OpenAI(
        api_key=args.openai_key,
        timeout=httpx.Timeout(None, connect=10, read=60, write=30),
    )

    # alt-text prompt
    if args.command == "generate-alt-text":
        propmt = f"Provide only the alt text for the image in {args.lang} language, describing the content in a concise, clear, and meaningful way. Focus on the essential details, conveying the purpose of the image for screen readers. Include relevant information about the image's context, objects, people, and any key actions or emotions, while keeping the description brief but informative."
    elif args.command == "generate-table-summary":
        propmt = f"Describe the table in {args.lang} language concisely without repeating its data. Keep the response brief and focus on structure, and content. Provide only the response without any additional explanation or context."
    elif args.command == "generate-mathml":
        propmt = f"Extract only the plain xml MathML {args.mathml_version} representation of the mathematical expression from the provided image, without any additional explanation, description, or markdown code formatting."
    else:
        raise ValueError(f"Unknown subparser value {args.subparser}")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": propmt,
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img}",
                        },
                    },
                ],
            },
        ],
        max_tokens=100,
    )

    return response.choices[0]
