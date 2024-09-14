from supabase import create_client
import os
from dotenv import load_dotenv
import uuid
import requests

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Assuming all classes are defined in the same file


class User:
    def __init__(
        self,
        id,
        username,
        name=None,
        bio=None,
        website=None,
        email=None,
        provider=None,
        password=None,
        badge=None,
        bgImage=None,
        profileImage=None,
        createdAt=None,
        followersCount=0,
        followingCount=0,
        likeCount=0,
        is_bot=False,
        bot_theme=None,
        bot_prompt=None,
        userProfile=None,
    ):
        self.id = id
        self.username = username
        self.name = name
        self.bio = bio
        self.website = website
        self.email = email
        self.provider = provider
        self.password = password
        self.badge = badge
        self.bgImage = bgImage
        self.profileImage = profileImage
        self.createdAt = createdAt
        self.followersCount = followersCount
        self.followingCount = followingCount
        self.likeCount = likeCount
        self.is_bot = is_bot  # For AI users
        self.bot_theme = bot_theme  # For AI users
        self.bot_prompt = bot_prompt  # For AI users

        # Load or create the associated profile
        self.userProfile = (
            userProfile
            or UserProfile.get_by_user_id(self.id)
            or UserProfile.create(self.id)
        )

    @classmethod
    def from_db(cls, user_data):
        return cls(
            id=user_data["id"],
            username=user_data["username"],
            name=user_data.get("name"),
            bio=user_data.get("bio"),
            website=user_data.get("website"),
            email=user_data.get("email"),
            provider=user_data.get("provider"),
            password=user_data.get("password"),
            badge=user_data.get("badge"),
            bgImage=user_data.get("bgImage"),
            profileImage=user_data.get("profileImage"),
            createdAt=user_data.get("createdAt"),
            followersCount=user_data.get("followersCount", 0),
            followingCount=user_data.get("followingCount", 0),
            likeCount=user_data.get("likeCount", 0),
            is_bot=user_data.get("isBot", False),
            bot_theme=user_data.get("botTheme"),
            bot_prompt=user_data.get("botPrompt"),
        )

    @classmethod
    def get_by_id(cls, user_id):
        response = supabase.table("User").select("*").eq("id", user_id).execute()
        if response.error:
            raise Exception(f"Error fetching user: {response.error}")
        if response.data:
            return cls.from_db(response.data[0])
        else:
            return None

    @classmethod
    def create(
        cls,
        username,
        name=None,
        bio=None,
        website=None,
        email=None,
        provider=None,
        password=None,
        badge=None,
        bgImage=None,
        profileImage=None,
        is_bot=False,
        bot_theme=None,
        bot_prompt=None,
    ):
        user_id = str(uuid.uuid4())
        data = {
            "id": user_id,
            "username": username,
            "name": name,
            "bio": bio,
            "website": website,
            "email": email,
            "provider": provider or "local",
            "password": password,
            "badge": badge,
            "bgImage": bgImage,
            "profileImage": profileImage,
            "createdAt": "now()",
            "followersCount": 0,
            "followingCount": 0,
            "likeCount": 0,
            "isBot": is_bot,
            "botTheme": bot_theme,
            "botPrompt": bot_prompt,
        }
        response = supabase.table("User").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating user: {response.error}")
        return cls.from_db(data)

    def tweet(self, content, images=None):
        # Create a tweet by this user
        return Tweet.create(user_id=self.id, body=content, images=images)

    def reply(self, tweet_id, content, images=None):
        # Reply to a tweet
        return Reply.create(
            user_id=self.id, tweet_id=tweet_id, body=content, images=images
        )

    def follow(self, target_user_id):
        data = {
            "id": str(uuid.uuid4()),
            "followerId": self.id,
            "followingId": target_user_id,
            "createdAt": "now()",
        }
        response = supabase.table("UserFollow").insert(data).execute()
        if response.error:
            raise Exception(f"Error following user: {response.error}")
        # Update following counts
        supabase.table("User").update({"followingCount": self.followingCount + 1}).eq(
            "id", self.id
        ).execute()
        supabase.table("User").update(
            {"followersCount": supabase.func("followersCount + 1")}
        ).eq("id", target_user_id).execute()
        return True

    def like_tweet(self, tweet_id):
        Like.create(user_id=self.id, tweet_id=tweet_id)

    def retweet_tweet(self, tweet_id):
        Retweet.create(user_id=self.id, tweet_id=tweet_id)

    def bookmark_tweet(self, tweet_id):
        Bookmark.create(user_id=self.id, tweet_id=tweet_id)

    def get_following(self):
        response = (
            supabase.table("UserFollow")
            .select("followingId")
            .eq("followerId", self.id)
            .execute()
        )
        if response.error:
            raise Exception(f"Error fetching following: {response.error}")
        following_ids = [record["followingId"] for record in response.data]
        return [User.get_by_id(user_id) for user_id in following_ids]

    def get_followers(self):
        response = (
            supabase.table("UserFollow")
            .select("followerId")
            .eq("followingId", self.id)
            .execute()
        )
        if response.error:
            raise Exception(f"Error fetching followers: {response.error}")
        follower_ids = [record["followerId"] for record in response.data]
        return [User.get_by_id(user_id) for user_id in follower_ids]

    def get_liked_tweets(self):
        response = (
            supabase.table("Like").select("tweetId").eq("userId", self.id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching liked tweets: {response.error}")
        tweet_ids = [record["tweetId"] for record in response.data]
        return [Tweet.get_by_id(tweet_id) for tweet_id in tweet_ids]

    def get_retweets(self):
        response = (
            supabase.table("Retweet").select("tweetId").eq("userId", self.id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching retweets: {response.error}")
        tweet_ids = [record["tweetId"] for record in response.data]
        return [Tweet.get_by_id(tweet_id) for tweet_id in tweet_ids]

    def get_bookmarks(self):
        response = (
            supabase.table("Bookmark").select("tweetId").eq("userId", self.id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching bookmarks: {response.error}")
        tweet_ids = [record["tweetId"] for record in response.data]
        return [Tweet.get_by_id(tweet_id) for tweet_id in tweet_ids]

    @classmethod
    def get_all_users(cls):
        response = supabase.table("User").select("*").execute()
        if response.error:
            raise Exception(f"Error fetching users: {response.error}")
        return [cls.from_db(user_data) for user_data in response.data]

    def update_profile(self, **kwargs):
        # Update the profile with new information
        for key, value in kwargs.items():
            if hasattr(self.userProfile, key):
                setattr(self.userProfile, key, value)
        self.userProfile.update()


class UserProfile:
    def __init__(
        self,
        user_id,
        age_group=None,
        gender=None,
        race=None,
        location=None,
        income_range=None,
        relationship_status=None,
        education=None,
        occupation=None,
        interests=None,
        created_at=None,
    ):
        self.user_id = user_id
        self.age_group = age_group
        self.gender = gender
        self.race = race
        self.location = location
        self.income_range = income_range
        self.relationship_status = relationship_status
        self.education = education
        self.occupation = occupation
        self.interests = interests or []
        self.created_at = created_at

    @classmethod
    def from_db(cls, profile_data):
        return cls(
            user_id=profile_data["userId"],
            age_group=profile_data.get("ageGroup"),
            gender=profile_data.get("gender"),
            race=profile_data.get("race"),
            location=profile_data.get("location"),
            income_range=profile_data.get("incomeRange"),
            relationship_status=profile_data.get("relationshipStatus"),
            education=profile_data.get("education"),
            occupation=profile_data.get("occupation"),
            interests=profile_data.get("interests", []),
            created_at=profile_data.get("createdAt"),
        )

    @classmethod
    def get_by_user_id(cls, user_id):
        response = (
            supabase.table("UserProfile").select("*").eq("userId", user_id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching user profile: {response.error}")
        if response.data:
            return cls.from_db(response.data[0])
        else:
            return None

    @classmethod
    def create(
        cls,
        user_id,
        age_group=None,
        gender=None,
        race=None,
        location=None,
        income_range=None,
        relationship_status=None,
        education=None,
        occupation=None,
        interests=None,
    ):
        data = {
            "userId": user_id,
            "ageGroup": age_group,
            "gender": gender,
            "race": race,
            "location": location,
            "incomeRange": income_range,
            "relationshipStatus": relationship_status,
            "education": education,
            "occupation": occupation,
            "interests": interests or [],
            "createdAt": "now()",
        }
        response = supabase.table("UserProfile").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating user profile: {response.error}")
        return cls.from_db(data)

    def update(self):
        data = {
            "ageGroup": self.age_group,
            "gender": self.gender,
            "race": self.race,
            "location": self.location,
            "incomeRange": self.income_range,
            "relationshipStatus": self.relationship_status,
            "education": self.education,
            "occupation": self.occupation,
            "interests": self.interests,
        }
        response = (
            supabase.table("UserProfile")
            .update(data)
            .eq("userId", self.user_id)
            .execute()
        )
        if response.error:
            raise Exception(f"Error updating user profile: {response.error}")
        return True


class Tweet:
    def __init__(
        self,
        id,
        user_id,
        body,
        images=None,
        likeCount=0,
        retweetCount=0,
        replyCount=0,
        createdAt=None,
    ):
        self.id = id
        self.user_id = user_id
        self.body = body
        self.images = images if images is not None else []
        self.likeCount = likeCount
        self.retweetCount = retweetCount
        self.replyCount = replyCount
        self.createdAt = createdAt

    @classmethod
    def from_db(cls, tweet_data):
        return cls(
            id=tweet_data["id"],
            user_id=tweet_data["userId"],
            body=tweet_data["body"],
            images=tweet_data.get("images", []),
            likeCount=tweet_data.get("likeCount", 0),
            retweetCount=tweet_data.get("retweetCount", 0),
            replyCount=tweet_data.get("replyCount", 0),
            createdAt=tweet_data.get("createdAt"),
        )

    @classmethod
    def create(cls, user_id, body, images=None):
        if images is None:
            images = []
        tweet_id = str(uuid.uuid4())
        data = {
            "id": tweet_id,
            "userId": user_id,
            "body": body,
            "images": images,
            "likeCount": 0,
            "retweetCount": 0,
            "replyCount": 0,
            "createdAt": "now()",
        }
        response = supabase.table("Tweet").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating tweet: {response.error}")
        return cls(
            id=tweet_id, user_id=user_id, body=body, images=images, createdAt="now()"
        )

    @classmethod
    def get_by_id(cls, tweet_id):
        response = supabase.table("Tweet").select("*").eq("id", tweet_id).execute()
        if response.error:
            raise Exception(f"Error fetching tweet: {response.error}")
        if response.data:
            return cls.from_db(response.data[0])
        else:
            return None

    @classmethod
    def get_all_tweets(cls):
        response = supabase.table("Tweet").select("*").execute()
        if response.error:
            raise Exception(f"Error fetching tweets: {response.error}")
        return [cls.from_db(tweet_data) for tweet_data in response.data]

    @classmethod
    def get_recent_tweets(cls, limit=10):
        response = (
            supabase.table("Tweet")
            .select("*")
            .order("createdAt", desc=True)
            .limit(limit)
            .execute()
        )
        if response.error:
            raise Exception(f"Error fetching tweets: {response.error}")
        return [cls.from_db(tweet_data) for tweet_data in response.data]

    def get_replies(self):
        response = supabase.table("Reply").select("*").eq("tweetId", self.id).execute()
        if response.error:
            raise Exception(f"Error fetching replies: {response.error}")
        return [Reply.from_db(reply_data) for reply_data in response.data]

    def get_likes(self):
        response = (
            supabase.table("Like").select("userId").eq("tweetId", self.id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching likes: {response.error}")
        user_ids = [record["userId"] for record in response.data]
        return [User.get_by_id(user_id) for user_id in user_ids]

    def get_retweets(self):
        response = (
            supabase.table("Retweet").select("userId").eq("tweetId", self.id).execute()
        )
        if response.error:
            raise Exception(f"Error fetching retweets: {response.error}")
        user_ids = [record["userId"] for record in response.data]
        return [User.get_by_id(user_id) for user_id in user_ids]

    def like(self, user_id):
        Like.create(user_id=user_id, tweet_id=self.id)

    def retweet(self, user_id):
        Retweet.create(user_id=user_id, tweet_id=self.id)

    def reply(self, user_id, content, images=None):
        Reply.create(user_id=user_id, tweet_id=self.id, body=content, images=images)


class Reply:
    def __init__(self, id, user_id, tweet_id, body, images=None, createdAt=None):
        self.id = id
        self.user_id = user_id
        self.tweet_id = tweet_id
        self.body = body
        self.images = images if images is not None else []
        self.createdAt = createdAt

    @classmethod
    def create(cls, user_id, tweet_id, body, images=None):
        if images is None:
            images = []
        reply_id = str(uuid.uuid4())
        data = {
            "id": reply_id,
            "userId": user_id,
            "tweetId": tweet_id,
            "body": body,
            "images": images,
            "createdAt": "now()",
        }
        response = supabase.table("Reply").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating reply: {response.error}")
        # Increment reply count
        supabase.table("Tweet").update(
            {"replyCount": supabase.func("replyCount + 1")}
        ).eq("id", tweet_id).execute()
        return cls(
            id=reply_id,
            user_id=user_id,
            tweet_id=tweet_id,
            body=body,
            images=images,
            createdAt="now()",
        )


class Retweet:
    def __init__(self, id, tweet_id, user_id, retweetDate):
        self.id = id
        self.tweet_id = tweet_id
        self.user_id = user_id
        self.retweetDate = retweetDate

    @classmethod
    def create(cls, user_id, tweet_id):
        retweet_id = str(uuid.uuid4())
        data = {
            "id": retweet_id,
            "userId": user_id,
            "tweetId": tweet_id,
            "retweetDate": "now()",
        }
        response = supabase.table("Retweet").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating retweet: {response.error}")
        # Increment retweet count
        supabase.table("Tweet").update(
            {"retweetCount": supabase.func("retweetCount + 1")}
        ).eq("id", tweet_id).execute()
        return cls(
            id=retweet_id, user_id=user_id, tweet_id=tweet_id, retweetDate="now()"
        )


class Like:
    def __init__(self, id, user_id, tweet_id, createdAt):
        self.id = id
        self.user_id = user_id
        self.tweet_id = tweet_id
        self.createdAt = createdAt

    @classmethod
    def create(cls, user_id, tweet_id):
        like_id = str(uuid.uuid4())
        data = {
            "id": like_id,
            "userId": user_id,
            "tweetId": tweet_id,
            "createdAt": "now()",
        }
        response = supabase.table("Like").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating like: {response.error}")
        # Increment counts
        supabase.table("Tweet").update(
            {"likeCount": supabase.func("likeCount + 1")}
        ).eq("id", tweet_id).execute()
        # Update user's likeCount (likes received)
        tweet = Tweet.get_by_id(tweet_id)
        if tweet:
            supabase.table("User").update(
                {"likeCount": supabase.func("likeCount + 1")}
            ).eq("id", tweet.user_id).execute()
        return cls(id=like_id, user_id=user_id, tweet_id=tweet_id, createdAt="now()")


class Bookmark:
    def __init__(self, id, user_id, tweet_id, createdAt):
        self.id = id
        self.user_id = user_id
        self.tweet_id = tweet_id
        self.created_at = createdAt

    @classmethod
    def from_db(cls, bookmark_data):
        return cls(
            id=bookmark_data["id"],
            user_id=bookmark_data["userId"],
            tweet_id=bookmark_data["tweetId"],
            createdAt=bookmark_data["createdAt"],
        )

    @classmethod
    def create(cls, user_id, tweet_id):
        bookmark_id = str(uuid.uuid4())
        data = {
            "id": bookmark_id,
            "userId": user_id,
            "tweetId": tweet_id,
            "createdAt": "now()",
        }
        response = supabase.table("Bookmark").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating bookmark: {response.error}")
        return cls(
            id=bookmark_id, user_id=user_id, tweet_id=tweet_id, createdAt="now()"
        )


class Message:
    def __init__(self, id, sender_id, recipient_id, body, image, createdAt):
        self.id = id
        self.sender_id = sender_id
        self.recipient_id = recipient_id
        self.body = body
        self.image = image
        self.created_at = createdAt

    @classmethod
    def from_db(cls, message_data):
        return cls(
            id=message_data["id"],
            sender_id=message_data["senderId"],
            recipient_id=message_data["recipientId"],
            body=message_data["body"],
            image=message_data.get("image"),
            createdAt=message_data["createdAt"],
        )

    @classmethod
    def create(cls, sender_id, recipient_id, body, image=None):
        message_id = str(uuid.uuid4())
        data = {
            "id": message_id,
            "senderId": sender_id,
            "recipientId": recipient_id,
            "body": body,
            "image": image,
            "createdAt": "now()",
        }
        response = supabase.table("Message").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating message: {response.error}")
        return cls(
            id=message_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            body=body,
            image=image,
            createdAt="now()",
        )


class UserFollow:
    def __init__(self, id, follower_id, following_id, createdAt):
        self.id = id
        self.follower_id = follower_id
        self.following_id = following_id
        self.created_at = createdAt

    @classmethod
    def from_db(cls, follow_data):
        return cls(
            id=follow_data["id"],
            follower_id=follow_data["followerId"],
            following_id=follow_data["followingId"],
            createdAt=follow_data["createdAt"],
        )

    @classmethod
    def create(cls, follower_id, following_id):
        follow_id = str(uuid.uuid4())
        data = {
            "id": follow_id,
            "followerId": follower_id,
            "followingId": following_id,
            "createdAt": "now()",
        }
        response = supabase.table("UserFollow").insert(data).execute()
        if response.error:
            raise Exception(f"Error creating follow relationship: {response.error}")
        return cls(
            id=follow_id,
            follower_id=follower_id,
            following_id=following_id,
            createdAt="now()",
        )


def download_image_from_url(supabase_url, output_directory):

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    filename = os.path.basename(supabase_url)
    # Remove any query parameters from the filename
    filename = filename.split("?")[0]
    # Set the local file path
    local_file_path = os.path.join(output_directory, filename)
    try:
        # Download the image
        response = requests.get(supabase_url)
        response.raise_for_status()
        with open(local_file_path, "wb") as f:
            f.write(response.content)
        # print(f"Downloaded image to {local_file_path}")
        return local_file_path
    except requests.exceptions.RequestException as e:
        print(f"Failed to download background image: {e}")
        return None


def set_image_and_get_url(src_file):

    if not os.path.isfile(src_file):
        print("Source file not found.")
        return None

    with open(src_file, "rb") as f:
        data = f.read()

    # Upload the image to the storage bucket
    response = supabase.storage.from_("images").upload(src_file, data)
    print(response)
    if response.status_code != "200":
        print(f"Error uploading image: {response.__dict__}")
    else:
        print("Image uploaded successfully.")

    # Generate the public URL
    public_url = supabase.storage.from_("images").get_public_url(src_file)
    return public_url
