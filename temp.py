# ai_content_inserter.py
from supabase import create_client, Client
import os
import uuid
import asyncio
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# Path to the local image file you want to upload
local_file_path = "public/bird.png"

# Desired file name in the storage bucket
storage_file_name = "ai_user_profile.png"

# Read the image file
with open(local_file_path, "rb") as f:
    data = f.read()

# Upload the image to the storage bucket
# response = supabase.storage.from_("images").upload(storage_file_name, data)


# Generate the public URL
public_url = supabase.storage.from_("images").get_public_url(storage_file_name)

print(f"Public URL: {public_url} : {type(public_url)}")


# Mock AI-generated tweets
ai_tweets = ["Hi, this is a test of a post by a user with a profile picture."]

# Mock AI-generated users
ai_users = [
    {
        "username": "BirdMan",
        "name": "AI2",
        "provider": "local",
        "profile_pic": public_url,
    }
    # Add more users...
]


async def insert_users():
    for user in ai_users:
        # Generate a UUID for the user ID
        user_id = str(uuid.uuid4())
        data = {
            "id": user_id,
            "username": user["username"],
            "name": user["name"],
            "provider": user["provider"],
            "createdAt": "now()",
            "profileImage": public_url,
        }
        response = supabase.table("User").insert(data).execute()
        print(f"Inserted user: {user['username']} with ID: {user_id}")


async def insert_tweets():
    # Fetch AI users from the database to get their IDs
    response = supabase.table("User").select("id", "username").execute()
    ai_user_ids = [
        user["id"]
        for user in response.data
        if user["username"] in [u["username"] for u in ai_users]
    ]

    for tweet_body in ai_tweets:
        # Randomly assign a tweet to an AI user
        user_id = ai_user_ids[0]  # Simplified for example; you can randomize this
        data = {
            "id": str(uuid.uuid4()),
            "userId": user_id,
            "body": tweet_body,
            "images": [public_url],
            "createdAt": "now()",
        }
        response = supabase.table("Tweet").insert(data).execute()
        print(f"Inserted tweet: {tweet_body[:30]}... by user ID: {user_id}")


async def main():
    # await insert_users()
    await insert_tweets()


if __name__ == "__main__":
    asyncio.run(main())
