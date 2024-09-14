from supabase import create_client, Client
from datatypes import *
from analyze import *
import requests
import os
from openai import OpenAI
from PIL import Image
from io import BytesIO
import base64
import json
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List
import random

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)
image_cache = {}

# Initialize Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

AYFIE_API_KEY = os.getenv("AYFIE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SD_API_KEY = os.getenv("SD_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def generate_targeted_content(author_user_id, target_user_id, prompt_topic=None):
    """Generate targeted content using the author and target user profiles and an optional prompt topic."""

    # Step 1: Fetch the author's name and bio
    author_response = (
        supabase.from_("User")
        .select("name, bio")
        .eq("id", author_user_id)
        .single()
        .execute()
    )

    author_data = author_response.data
    author_name = author_data.get("name", "Anonymous")
    author_bio = author_data.get("bio", "")

    # Step 2: Fetch the target user's profile

    target_basic_response = (
        supabase.from_("User")
        .select("name,bio,username")
        .eq("id", target_user_id)
        .single()
        .execute()
    )

    target_basic = target_basic_response.data
    target_name = target_basic.get("name", "Anonymous")
    target_username = target_basic.get("username", "Anonymous")
    target_bio = target_basic.get("bio", "")

    try:
        target_profile_response = (
            supabase.from_("UserProfile")
            .select("*")
            .eq("userId", target_user_id)
            .single()
            .execute()
        )

        target_profile = target_profile_response.data
    except:
        target_profile = {}
    # If no target profile exists, raise an exception or handle it as needed
    # if not target_profile or target_profile == {}:
    #    return f"Error: Target user profile not found for user ID {target_user_id}"

    # Step 3: Construct the prompt for GPT-4o-mini
    prompt = f"""
    You are {author_name}. Your bio says: "{author_bio}".
    You are writing a personalized post, written in a tone and formality level corresponding to your image as described in your bio. This personalized post is directed for a person with the following profile:


    Name: {target_name}
    Username: {target_username}
    Bio: {target_bio}
    
    Age Group: {target_profile.get('ageGroup', 'unknown')}
    Gender: {target_profile.get('gender', 'unknown')}
    Race: {target_profile.get('race', 'unknown')}
    Location: {target_profile.get('location', 'unknown')}
    Income Range: {target_profile.get('incomeRange', 'unknown')}
    Relationship Status: {target_profile.get('relationshipStatus', 'unknown')}
    Education: {target_profile.get('education', 'unknown')}
    Occupation: {target_profile.get('occupation', 'unknown')}
    Interests: {', '.join(target_profile.get('interests', []))}
    Additional Facts: {', '.join(target_profile.get('facts', []))}

    """

    if prompt_topic:
        prompt += f"Post Topic: {prompt_topic}\n"

    prompt += "Write a post with this information in mind. If no post topic is specified, talk about something that interests or relates to the target, but make it subtle. Rather, moreso ensure that whatever you write about is aligned and natural in both content and style described in your bio. For example, someone who's bio mentions that they're a car salesman, should porbably speak in a sales-y way and post ads. etc.\n"
    prompt += "Do not explicitly tailor your post for the target user, rather, subtley shape your post so that it is aligned to what the target user would like, given their demographics and background.\nAdditionally, ensure you speak in a somewhat blase and casual tone, and be cold and somewhat rude and very blunt.\n"
    prompt += "Keep your results very short, under 140 characters\n"

    # Step 4: Use GPT-4o-mini to generate content
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a personalized content generator."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=50,
    )

    # Extract and return the generated content
    try:
        generated_content = response.choices[0].message.content
        return generated_content
    except:
        return ""


def generate_image(prompt, output_path):

    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/core",
        headers={"authorization": f"Bearer {SD_API_KEY}", "accept": "image/*"},
        files={"none": ""},
        data={
            "prompt": prompt,
            "output_format": "jpeg",
        },
    )

    if response.status_code == 200:
        with open(output_path, "wb") as file:
            file.write(response.content)
    else:
        raise Exception(str(response.json()))


def generate_image_cheap(prompt, output_path):

    engine_id = "stable-diffusion-xl-1024-v1-0"
    api_host = "https://api.stability.ai"
    if SD_API_KEY is None:
        raise Exception("Missing Stability API key.")

    response = requests.post(
        f"{api_host}/v1/generation/{engine_id}/text-to-image",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {SD_API_KEY}",
        },
        json={
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
        },
    )

    if response.status_code != 200:
        raise Exception("Non-200 response: " + str(response.text))

    data = response.json()

    for i, image in enumerate(data["artifacts"]):
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image["base64"]))
