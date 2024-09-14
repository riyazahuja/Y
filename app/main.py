from collect_data import *
from generate import *
from datatypes import set_image_and_get_url
import random
import time
import datetime
from collections import defaultdict
import math

# Ratio of AI users to human users
TARGET_AI_HUMAN_RATIO = 1.5  # Example: 1.5 AI users for every 1 human user


class UserSeed(BaseModel):
    name: str = Field(description="User's full name")
    username: str = Field(description="User's username (must be unique)")
    bio: str = Field(
        description="a short description of who the user is and what they do"
    )


class UserSeedList(BaseModel):
    contents: List[UserSeed]


max_bios_generated_batch = 5


def generate_bios(n=max_bios_generated_batch):

    completion = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"Generate a basic description of a random user of a social media site. For example, you could have a person named 'John Doe' with username 'jdoe99' and a bio 'I like video games and selling them to people', or 'Jane Smith' with username 'jsmithhh' and a bio 'Still waiting for JB's next album...' for users who will post ads and post music content respectively. Similarly, generate exactly {n} such basic user description and return them as a list. Feel free to be creative and random in choosing what each of the generated user signatures does, whether it be selling, music, technology, or any other interest - as well as how they do it: funny, casual, formal, rude, etc.",
            },
            {
                "role": "user",
                "content": f"Generate exactly {n} user names,usernames, and bio's that are all unique and distinct in their interests and purpose.",
            },
        ],
        response_format=UserSeedList,
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
        return ""


def maintain_ai_human_ratio():
    """Check the number of human and AI users and ensure the ratio is maintained."""
    humans = supabase.from_("User").select("id").neq("provider", "ai").execute().data
    ais = supabase.from_("User").select("id").eq("provider", "ai").execute().data

    human_count = len(humans)
    ai_count = len(ais)

    current_ratio = ai_count / max(human_count, 1)
    if current_ratio < TARGET_AI_HUMAN_RATIO:
        # Calculate how many new AI users are needed
        ai_needed = int((TARGET_AI_HUMAN_RATIO * human_count) - ai_count)
        ai_seeds = []
        for _ in range(ai_needed // max_bios_generated_batch):
            seeds = generate_bios()
            ai_seeds.extend(seeds)
        last_seed = generate_bios(n=ai_needed % max_bios_generated_batch)
        ai_seeds.extend(last_seed)

        for seed in ai_seeds:
            create_ai_user(seed, human_count, ai_count)
            print(f"created new AI user with username {seed.username}")


def create_ai_user(seed, human_cnt, ai_cnt):
    """Create a new AI user in the system."""

    has_profile = random.random() < 0.6
    has_background = random.random() < 0.15

    if has_profile:
        output_path = os.path.join("app", "cache", str(uuid.uuid4()).replace("-", ""))
        generate_image_cheap(
            f"A profile picture of a person named {seed.name} whos bio is {seed.bio}",
            output_path,
        )
        profile_url = set_image_and_get_url(output_path)
    if has_background:
        output_path = os.path.join("app", "cache", str(uuid.uuid4()).replace("-", ""))
        generate_image_cheap(
            f"A background image for a twitter profile for a someone who {seed.bio}",
            output_path,
        )
        background_url = set_image_and_get_url(output_path)

    profile_data = {
        "id": str(uuid.uuid4()),
        "username": seed.username,
        "name": seed.name,
        "bio": seed.bio,
        "provider": "ai",  # Marks this user as an AI user
        "createdAt": str(datetime.datetime.utcnow()),
        "followersCount": random.randint(
            (human_cnt + ai_cnt) // 4, 3 * (human_cnt + ai_cnt) // 4
        ),
        "followingCount": random.randint(
            (human_cnt + ai_cnt) // 4, 3 * (human_cnt + ai_cnt) // 4
        ),
    }
    if has_profile:
        profile_data["profileImage"] = profile_url
    if has_background:
        profile_data["bgImage"] = background_url

    if random.random() < 0.2:
        profile_data["badge"] = "blue"

    supabase.from_("User").insert(profile_data).execute()

    print(f"Created new AI user: {profile_data['username']}")


def get_user_last_activity():
    """Fetch the latest activity (tweets or replies) for each user."""

    # Step 1: Fetch the latest tweet for each user
    tweet_activity = (
        supabase.from_("Tweet")
        .select("userId, createdAt")
        .order("createdAt", desc=True)
        .execute()
        .data
    )

    # Step 2: Fetch the latest reply for each user
    reply_activity = (
        supabase.from_("Reply")
        .select("userId, createdAt")
        .order("createdAt", desc=True)
        .execute()
        .data
    )

    return tweet_activity, reply_activity


def parse_timestamp(timestamp_str):
    """Parse a timestamp string and handle various formats."""
    # Try parsing with two-digit fractional seconds
    try:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        pass  # Fall through to next attempt

    # Try parsing without fractional seconds
    try:
        return datetime.datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        raise ValueError(f"Could not parse timestamp: {timestamp_str}")


def combine_user_activity(tweet_activity, reply_activity):
    """Combine tweet and reply activity to find the latest activity for each user."""

    user_last_activity = defaultdict(lambda: datetime.datetime.min)

    # Step 1: Process tweet activity
    for tweet in tweet_activity:
        user_id = tweet["userId"]
        created_at = parse_timestamp(tweet["createdAt"])

        # Update the latest activity for this user if this tweet is more recent
        if created_at > user_last_activity[user_id]:
            user_last_activity[user_id] = created_at

    # Step 2: Process reply activity
    for reply in reply_activity:
        user_id = reply["userId"]
        created_at = parse_timestamp(reply["createdAt"])

        # Update the latest activity for this user if this reply is more recent
        if created_at > user_last_activity[user_id]:
            user_last_activity[user_id] = created_at

    return user_last_activity


def filter_and_sort_users_by_activity(user_last_activity, limit=10):
    """Filter out AI users and sort by the latest activity."""

    # Fetch all users with their `provider` field to distinguish AI from humans
    users = (
        supabase.from_("User")
        .select("id, provider")
        .in_("id", list(user_last_activity.keys()))  # Only get users that have activity
        .execute()
        .data
    )

    # Filter out AI users and create a list of tuples (user_id, last_activity)
    human_users = [
        (user["id"], user_last_activity[user["id"]])
        for user in users
        if user["provider"] != "ai"  # Filter out AI users
    ]

    ai_users = [
        (user["id"], user_last_activity[user["id"]])
        for user in users
        if user["provider"] == "ai"  # Filter out AI users
    ]

    # Sort by latest activity (most recent first)
    if random.random() < 0.5:
        human_users = human_users + ai_users
        ai_users = []

    sorted_human_users = sorted(human_users, key=lambda x: x[1], reverse=True)
    sorted_ai_users = sorted(ai_users, key=lambda x: x[1], reverse=True)

    # Return the top `limit` users
    return (sorted_human_users + sorted_ai_users)[:limit]


def get_recent_active_users(limit=10):
    """Get the most recent active users (both tweet and reply) and filter out AI users."""

    # Step 1: Get user activity data
    tweet_activity, reply_activity = get_user_last_activity()

    # Step 2: Combine the tweet and reply activity to find the latest activity per user
    user_last_activity = combine_user_activity(tweet_activity, reply_activity)

    # Step 3: Filter out AI users and sort by latest activity
    sorted_human_users = filter_and_sort_users_by_activity(user_last_activity, limit)

    return sorted_human_users


def post_ai_comment(author_user_id, target_user_id, tweet_id):
    """AI user posts a comment on a target user's tweet."""
    tweet_response = (
        supabase.from_("Tweet")
        .select("body, images,replyCount")
        .eq("id", tweet_id)
        .single()
        .execute()
    )
    tweet_data = tweet_response.data  # get("data", {})
    tweet_content = tweet_data.get("body", "")
    tweet_images = tweet_data.get("images", [])
    tweet_replyCount = tweet_data.get("replyCount", 0)
    # Create the prompt for AI comment generation with tweet content
    prompt_topic = f"comment on this tweet: '{tweet_content}'\n"
    if tweet_images:
        prompt_topic += "(there are associated images as well)\n"
    prompt_topic += "Make sure that the content and tone of the output is aligned with your character description given in your bio."

    content = generate_targeted_content(
        author_user_id, target_user_id, prompt_topic=prompt_topic
    )
    reply_data = {
        "id": str(uuid.uuid4()),
        "userId": author_user_id,
        "tweetId": tweet_id,
        "body": content,
        "createdAt": str(datetime.datetime.utcnow()),
        "images": [],
    }
    supabase.from_("Reply").insert(reply_data).execute()
    supabase.from_("Tweet").update({"replyCount": tweet_replyCount + 1}).eq(
        "id", tweet_id
    ).execute()

    print(f"AI user {author_user_id} commented on tweet {tweet_id}")


def post_ai_like(author_user_id, tweet_id):
    """AI user likes a target user's tweet."""
    like_data = {
        "id": str(uuid.uuid4()),
        "userId": author_user_id,
        "tweetId": tweet_id,
        "createdAt": str(datetime.datetime.utcnow()),
    }
    tweet_response = (
        supabase.from_("Tweet")
        .select("likeCount")
        .eq("id", tweet_id)
        .single()
        .execute()
    )
    tweet_data = tweet_response.data
    tweet_likeCount = tweet_data.get("likeCount", 0)
    supabase.from_("Like").insert(like_data).execute()
    supabase.from_("Tweet").update({"likeCount": tweet_likeCount + 1}).eq(
        "id", tweet_id
    ).execute()

    print(f"AI user {author_user_id} liked tweet {tweet_id}")


def post_ai_tweet(author_user_id, target_user_id):
    """AI user posts a new tweet targeting a specific user."""
    content = generate_targeted_content(author_user_id, target_user_id)

    # 30% chance to include an image
    if random.random() < 0.25:
        output_path = os.path.join("app", "cache", str(uuid.uuid4()).replace("-", ""))
        generate_image_cheap(content, output_path)
        url = set_image_and_get_url(output_path)
        tweet_data = {
            "id": str(uuid.uuid4()),
            "userId": author_user_id,
            "body": content,
            "createdAt": str(datetime.datetime.utcnow()),
            "images": [url],
        }
    else:
        tweet_data = {
            "id": str(uuid.uuid4()),
            "userId": author_user_id,
            "body": content,
            "createdAt": str(datetime.datetime.utcnow()),
            "images": [],
        }

    supabase.from_("Tweet").insert(tweet_data).execute()
    print(f"AI user {author_user_id} posted a new tweet targeted at {target_user_id}")


def assign_ai_interactions(tweet_id, human_user_id, num_comments=3, num_likes=5):
    """Assign AI users to interact with a human post."""
    # Get AI users to interact with the post
    ai_users = (
        supabase.from_("User")
        .select("id")
        .eq("provider", "ai")
        # .limit(num_comments + num_likes)
        .execute()
        .data  # .get("data", [])
    )
    if num_comments + num_likes < len(ai_users):
        ai_users = random.sample(ai_users, num_comments + num_likes)
    # print(ai_users)

    # Assign comments
    print(num_comments)
    for i in range(num_comments):
        ai_user_id = ai_users[i]["id"]
        post_ai_comment(ai_user_id, human_user_id, tweet_id)
        print(f"ai comment posted")

    # Assign likes
    for i in range(num_comments, min(num_comments + num_likes, len(ai_users))):
        ai_user_id = ai_users[i]["id"]
        post_ai_like(ai_user_id, tweet_id)
        print(f"ai like posted")


def main_driver_loop():
    """Main loop that manages AI posting behavior and interactions."""

    # Maintain the AI-to-human ratio
    maintain_ai_human_ratio()
    print("ratio maintained")
    # Get the most recent human tweets
    recent_tweets = (
        supabase.from_("Tweet")
        .select("id, userId, createdAt")
        .order("createdAt", desc=True)
        .limit(10)
        .execute()
        .data
    )

    user_ids = [tweet["userId"] for tweet in recent_tweets]

    # Fetch the users associated with these user IDs
    users = (
        supabase.from_("User").select("id, provider").in_("id", user_ids).execute().data
    )

    # Create a dictionary for easy lookup of user info by userId
    user_dict = {user["id"]: user for user in users}

    # Filter out tweets by AI users
    filtered_tweets = [
        tweet
        for tweet in recent_tweets
        if user_dict.get(tweet["userId"], {}).get("provider")
        != "ai"  # or random.random() < 0.4
    ]

    # num_users = len(supabase.from_("User").select("id").execute().data)

    # Assign AI interactions to human posts
    for tweet in filtered_tweets:
        human_user_id = tweet["userId"]
        tweet_id = tweet["id"]
        num_comments = math.floor(random.randint(0, 3) / 3)  # 3-6 comments
        num_likes = math.floor(random.randint(0, 2) / 2)
        assign_ai_interactions(tweet_id, human_user_id, num_comments, num_likes)

    print("interactions completed")

    recent_users = get_recent_active_users(limit=10)

    # Make AI users create posts targeting randomly selected recently active users
    ai_users = (
        supabase.from_("User").select("id").eq("provider", "ai").limit(5).execute().data
    )

    ai_user = random.choice(ai_users)

    # AI users post tweets targeting random recently active users

    target_user = random.choice(recent_users)[0]  # Get the user_id of a recent user
    post_ai_tweet(ai_user["id"], target_user)
    print("post completed")

    human_users = (
        supabase.from_("User").select("id").neq("provider", "ai").execute().data
    )
    for human in human_users:
        analyze_and_update_user_profile(human.get("id", ""))
    print("Profile updates complete")
    print("loop complete, sleeping 45s")
    # Repeat the process after a certain interval (e.g., 60 seconds)
    time.sleep(45)
    main_driver_loop()


# Run the main driver loop
main_driver_loop()
