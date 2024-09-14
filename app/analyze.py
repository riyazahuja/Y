# import types
import time
import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
import base64
from PIL import Image
from io import BytesIO
import hashlib


load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)


AYFIE_API_KEY = os.getenv("AYFIE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_keywords(text: str, top_n=5, ngram_range=(1, 1)):
    url = "https://portal.ayfie.com/api/keyword"
    headers = {
        "accept": "application/json",
        "X-API-KEY": AYFIE_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "top_n": top_n,
        "ngram_range": ngram_range,
        "diversify": False,
        "diversity": 0.7,
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()

        # Extract keywords from the response
        keywords = data.get("result", {})
        return keywords

    except requests.exceptions.RequestException as e:
        print(f"Error in analyzing text: {e}\n{text} : {type(text)}")
        return {}


def get_img_description(path_to_image, max_width=1024, max_height=1024):
    client = OpenAI()

    with Image.open(path_to_image) as img:
        # Get original image dimensions
        original_width, original_height = img.size
        # print(f"Original dimensions: {original_width}x{original_height}")

        # Check if the image needs to be resized
        if original_width > max_width or original_height > max_height:
            # Calculate the scaling factor to maintain the aspect ratio
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scaling_factor = min(width_ratio, height_ratio)

            # Calculate the new dimensions
            new_width = int(original_width * scaling_factor)
            new_height = int(original_height * scaling_factor)
            # print(f"Resized dimensions: {new_width}x{new_height}")

            # Resize the image
            resized_img = img.resize((new_width, new_height), Image.LANCZOS).convert(
                "RGB"
            )
            # Save the resized image to the output path

            buff = BytesIO()
            resized_img.save(buff, format="JPEG")
            img_str = base64.b64encode(buff.getvalue()).decode("utf-8")

            data = img_str

            # print(f"Image resized and saved")
        else:
            with open(path_to_image, "rb") as image_file:
                data = base64.b64encode(image_file.read()).decode("utf-8")
            # print("Image dimensions are within the limits, no resizing needed.")

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What’s in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{data}"},
                        },
                    ],
                }
            ],
            max_tokens=400,
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in analyzing image: {e}")
        return ""


def generate_cache_key(image_data):
    """Generate a cache key for an image based on its contents."""
    return hashlib.md5(image_data).hexdigest()


def get_image_description_with_cache(path_to_image, cache):
    """Check if image description is cached, if not, generate and cache it."""
    with open(path_to_image, "rb") as image_file:
        image_data = image_file.read()
        cache_key = generate_cache_key(image_data)

        # Check if the description is already cached
        if cache.get(cache_key):
            return cache[cache_key]

        # If not cached, generate a new description
        description = get_img_description(path_to_image)

        # Cache the result
        cache[cache_key] = description
        return description


# # Example usage:
# text_sample = (
#     "What are some names for a privacy-centered social network kinda like twitter"
# )
# keywords = get_keywords(text_sample)
# print(f"Keywords: {keywords}")
# cache = {}
# st = time.time()
# print(get_image_description_with_cache("public/bird.png", cache))
# mt = time.time()
# print(get_image_description_with_cache("public/bird.png", cache))
# print(f"first: {mt-st}\nsec: {time.time()-mt}")
