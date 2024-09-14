from supabase import create_client, Client
from datatypes import *
import pandas as pd
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


class strList(BaseModel):
    contents: List[str] = Field(
        description="One single advertising strategy/tactic, in less than 50 characters."
    )


def get_strategies(user_profile, n=3):
    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"You are an advertising strategy recommendation system, who analyzes some user data and gives a few examples of advertising strategies that would best target them, based on their demographics and interests and background.",
            },
            {
                "role": "user",
                "content": f"""Generate up to {n} advertising strategies (short, quick tactics that you decide would be effective in getting the user's business) based on the following user profile:
                
                Age Group: {user_profile.get('ageGroup', 'unknown')}
                Gender: {user_profile.get('gender', 'unknown')}
                Race: {user_profile.get('race', 'unknown')}
                Location: {user_profile.get('location', 'unknown')}
                Income Range: {user_profile.get('incomeRange', 'unknown')}
                Relationship Status: {user_profile.get('relationshipStatus', 'unknown')}
                Education: {user_profile.get('education', 'unknown')}
                Occupation: {user_profile.get('occupation', 'unknown')}
                Interests: {', '.join(user_profile.get('interests', []))}
                Additional Facts: {', '.join(user_profile.get('facts', []))}
                """,
            },
        ],
        max_tokens=n * 50,
        response_format=strList,
    )

    try:
        message = completion.choices[0].message
        if message.parsed:
            return message.parsed.__dict__.get("contents")
        else:
            raise ValueError("Invalid parse")
    except Exception as e:
        print(message.refusal)
        print(f"error:{e}")
        return []


# user_profiles = supabase.from_("UserProfile").select("*").execute().data
# for up in user_profiles:
#     print(get_strategies(up))


def export_user_profiles_to_pico_html():
    # Fetch all UserProfiles
    user_profiles = supabase.from_("UserProfile").select("*").execute().data

    # Fetch all Users (only the fields we need)
    users = supabase.from_("User").select("id, name, username").execute().data

    # Convert the data to DataFrames
    df_user_profiles = pd.DataFrame(user_profiles)

    df_user_profiles["strategies"] = df_user_profiles.apply(
        lambda row: " | ".join(get_strategies(row.to_dict())), axis=1
    )
    df_user_profiles["facts"] = df_user_profiles.apply(
        lambda row: " | ".join(row["facts"]), axis=1
    )
    df_user_profiles["interests"] = df_user_profiles.apply(
        lambda row: " | ".join(row["interests"]), axis=1
    )

    df_users = pd.DataFrame(users)

    # Merge the two DataFrames on the `userId` and `id` fields
    merged_df = pd.merge(
        df_user_profiles, df_users, left_on="userId", right_on="id", how="left"
    )

    # Drop the unnecessary `id_y` column from the `User` table
    merged_df.drop(columns=["id_y"], inplace=True)

    # Rename `id_x` to `userProfileId` to avoid confusion
    merged_df.rename(columns={"id_x": "userProfileId"}, inplace=True)

    # Reorder columns to place 'name' and 'username' first
    columns_order = ["name", "username"] + [
        col for col in merged_df.columns if col not in ["name", "username"]
    ]
    merged_df = merged_df[columns_order]

    # PicoCSS - Link to PicoCSS CDN
    pico_css = """
    <link rel="stylesheet" href="https://unpkg.com/@picocss/pico@1.*/css/pico.min.css">
    """

    # Create an HTML structure with PicoCSS
    html_header = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>User Profiles</title>
            {pico_css}
        </head>
        <body>
            <main class="container">
                <h1>User Profiles</h1>
    """

    # Convert the DataFrame to HTML
    html_table = merged_df.to_html(index=False, escape=False)

    # Add a footer and close the HTML tags
    html_footer = """
            </main>
        </body>
    </html>
    """

    # Combine the HTML parts
    final_html = html_header + html_table + html_footer

    # Save the final HTML to a file
    html_file_path = "user_profiles_pico.html"
    with open(html_file_path, "w") as f:
        f.write(final_html)

    print(f"UserProfiles have been exported to {html_file_path}")


# Call the function
export_user_profiles_to_pico_html()
