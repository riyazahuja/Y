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
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def get_recent_tweets(user_id, n):
    """Fetch the most recent n tweets for a user."""
    tweets_response = (
        supabase.from_("Tweet")
        .select("*")
        .eq("userId", user_id)
        .order("createdAt", desc=True)
        .limit(n)
        .execute()
    )
    return tweets_response.data


def get_recent_replies(user_id, m):
    """Fetch the most recent m replies for a user."""
    replies_response = (
        supabase.from_("Reply")
        .select("*, Tweet(body, images)")
        .eq("userId", user_id)
        .order("createdAt", desc=True)
        .limit(m)
        .execute()
    )

    return replies_response.data


def get_recent_likes(user_id, l):
    """Fetch the most recent l liked tweets for a user."""
    likes_response = (
        supabase.from_("Like")
        .select("*, Tweet(body, images)")
        .eq("userId", user_id)
        .order("createdAt", desc=True)
        .limit(l)
        .execute()
    )

    return likes_response.data


def analyze_user_data(user_id, n_tweets, m_replies, l_likes):
    # Fetch recent tweets, replies, and likes
    recent_tweets = get_recent_tweets(user_id, n_tweets)
    recent_replies = get_recent_replies(user_id, m_replies)
    recent_likes = get_recent_likes(user_id, l_likes)

    prev_profile = {}

    try:
        prev_profile_response = (
            supabase.from_("UserProfile")
            .select("*")
            .eq("userId", user_id)
            .single()
            .execute()
        )
    except Exception as e:
        prev_profile_response = None
        print(e)

    if prev_profile_response:
        prev_profile = prev_profile_response.data

    # Initialize cache for image descriptions

    all_analysis = {
        "tweets": [],
        "replies": [],
        "likes": [],
        "prevProfile": prev_profile,
    }

    # Analyze tweets
    for tweet in recent_tweets:
        text = tweet.get("body", "")
        keywords = get_keywords(text)
        images = tweet.get("images", [])
        images = [img for img in images if img != ""]
        img_descriptions = []
        for img_url in images:
            try:
                path = download_image_from_url(img_url, "app/cache")
                img_descriptions.append(
                    get_image_description_with_cache(path, image_cache)
                )
            except:
                pass
        all_analysis["tweets"].append(
            {"text": text, "keywords": keywords, "image_descriptions": img_descriptions}
        )

    # Analyze replies
    for reply in recent_replies:
        text = reply.get("body", "")
        keywords = get_keywords(text)
        tweet_images = reply.get("Tweet", {}).get("images", [])

        images = [img for img in tweet_images if img != ""]
        img_descriptions = []
        for img_url in images:
            try:
                path = download_image_from_url(img_url, "app/cache")
                img_descriptions.append(
                    get_image_description_with_cache(path, image_cache)
                )
            except:
                pass

        all_analysis["replies"].append(
            {"text": text, "keywords": keywords, "image_descriptions": img_descriptions}
        )

    # Analyze likes
    for like in recent_likes:
        tweet = like.get("Tweet", {})
        text = tweet.get("body", "")
        keywords = get_keywords(text)
        images = tweet.get("images", [])

        images = [img for img in images if img != ""]
        img_descriptions = []
        for img_url in images:
            try:
                path = download_image_from_url(img_url, "app/cache")
                img_descriptions.append(
                    get_image_description_with_cache(path, image_cache)
                )
            except:
                pass

        all_analysis["likes"].append(
            {"text": text, "keywords": keywords, "image_descriptions": img_descriptions}
        )

    return all_analysis


def analyze_user_profile(user_id):
    # Fetch user information from Supabase
    user_response = (
        supabase.from_("User")
        .select("name, bio, profileImage")
        .eq("id", user_id)
        .single()
        .execute()
    )

    user_data = user_response.data

    bio = user_data.get("bio", "")
    profile_image_url = user_data.get("profileImage")
    path = download_image_from_url(profile_image_url, "app/cache")

    profile_keywords = get_keywords(bio)

    profile_image_description = get_image_description_with_cache(path, image_cache)

    return {
        "name": user_data.get("name", ""),
        "bio": bio,
        "bio_keywords": profile_keywords,
        "profile_image_description": profile_image_description,
    }


def compile_profile_prompt(analysis, user_profile_analysis):
    # Combine all tweets, replies, and likes data
    combined_text = ""

    combined_text += f"Previous user profile data: \n{analysis['prevProfile']}\n\n\n"

    for tweet in analysis["tweets"]:
        combined_text += f"Tweet: {tweet['text']} \n"
        combined_text += f"Keywords: {tweet['keywords']} \n"
        combined_text += f"Images: {tweet['image_descriptions']} \n\n"

    for reply in analysis["replies"]:
        combined_text += f"Reply: {reply['text']} \n"
        combined_text += f"Keywords: {reply['keywords']} \n"
        combined_text += f"Images: {reply['image_descriptions']} \n\n"

    for like in analysis["likes"]:
        combined_text += f"Liked Tweet: {like['text']} \n"
        combined_text += f"Keywords: {like['keywords']} \n"
        combined_text += f"Images: {like['image_descriptions']} \n\n"

    # Add user profile analysis
    combined_text += f"User Bio: {user_profile_analysis['bio']} \n"
    combined_text += f"User Bio Keywords: {user_profile_analysis['bio_keywords']} \n"
    combined_text += f"Profile Image Description: {user_profile_analysis['profile_image_description']} \n"

    return combined_text


class UserProfile_BM(BaseModel):
    ageGroup: Optional[str] = Field(description="e.g., 18-25, 25-34, 43, etc.")
    gender: Optional[str] = Field(description="e.g., male, female, etc.")
    race: Optional[str] = Field(description="e.g., Caucasian, Asian, African American")
    location: Optional[str] = Field(description="e.g., City, Country, etc.")
    incomeRange: Optional[str] = Field(description="e.g., $30,000-$50,000,etc.")
    relationshipStatus: Optional[str] = Field(description="single, married,etc.")
    education: Optional[str] = Field(description="e.g., High school, masters, etc.")
    occupation: Optional[str] = Field(
        description="Mcdonald's worker, VP of customer relations at McKinsey, etc."
    )
    interests: List[str] = Field(
        description="e.g., ['technology', 'gaming', 'sports'] "
    )
    facts: List[str] = Field(description="e.g., Any other interesting or notable facts")


def generate_user_profile(combined_text):

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "Generate a detailed user profile based on the following information. Make your best estimates using the information you currently have for each category.\nFeel free to use ranges or lists of values if you believe that with the information you were given, that is the most accurate you may reasonably be. \nHowever, if you are unsure of something or don't have enough information to make a reasonable guess, you may leave that option blank. However, if you're unsure, it is better to take a very tentative and general guess than leave one blank, so only leave it blank if you have zero information regarding said category. If given a nonempty previous profile, prioritize those results over the tweet,reply,user, and like results, and only outweigh the previous profile if it directly contradicts it.",
            },
            {
                "role": "user",
                "content": f"Using the following information, ordered in priority from high to low priority, generate a user profile:\n{combined_text}",
            },
        ],
        response_format=UserProfile_BM,
    )

    try:
        message = completion.choices[0].message
        if message.parsed:
            return message
        else:
            raise ValueError("Invalid parse")
    except Exception as e:
        print(message.refusal)
        print(f"error:{e}")
        return ""


def update_user_profile(user_id, profile_json):
    """Update or insert the user profile in Supabase."""
    # Check if the user profile exists
    try:
        existing_profile_response = (
            supabase.from_("UserProfile")
            .select("id")
            .eq("userId", user_id)
            .single()
            .execute()
        )
    except:
        existing_profile_response = None

    if (
        existing_profile_response is not None and existing_profile_response.data
    ):  # If the profile exists, update it
        try:
            print(f"{profile_json} : {type(profile_json)}")
            profile_json["userId"] = user_id  # Add userId to the new profile
            profile_json["id"] = str(uuid.uuid4())

            update_response = (
                supabase.from_("UserProfile")
                .update(profile_json)
                .eq("userId", user_id)
                .execute()
            )
            # print(f"Profile updated for user: {user_id}")
        except Exception as e:
            print(f"Error updating profile: {e}")
    else:  # If no profile exists, insert a new one
        try:
            profile_json["userId"] = user_id  # Add userId to the new profile
            profile_json["id"] = str(uuid.uuid4())  # Add userId to the new profile

            supabase.from_("UserProfile").insert(profile_json).execute()
            # print(f"Profile created for user: {user_id}")
        except Exception as e:
            print(f"Error creating profile: {e}")


def analyze_and_update_user_profile(user_id, n_tweets=5, m_replies=3, l_likes=3):
    """Main function to analyze user data, generate profile, and update it."""

    # Step 1: Analyze user data (tweets, replies, likes)
    analysis = analyze_user_data(user_id, n_tweets, m_replies, l_likes)

    # Step 2: Analyze user profile information (bio, name, profile image)
    user_profile_analysis = analyze_user_profile(user_id)

    # Step 3: Compile the analysis data into a single prompt string
    combined_text = compile_profile_prompt(analysis, user_profile_analysis)

    # Step 4: Use GPT-4o-mini to generate the user profile JSON
    profile_data = json.loads(
        generate_user_profile(combined_text).__dict__.get("content")
    )

    # Step 6: Update the user's profile in Supabase
    update_user_profile(user_id, profile_data)

    print("User profile has been updated successfully.")
