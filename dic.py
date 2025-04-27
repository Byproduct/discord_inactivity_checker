# Discord inactivity checker
# Checks users that have a specific role for activity/inactivity in specific channels.
# (For example to revoke privileges from users that aren't using them.)

# Requires discord.py and tabulate
# Requires a new or offline bot invited into the server with user and channel access. 
# Do not use the token of a bot that is currently active - this script would interrupt whatever it is doing.

BOT_TOKEN = "" # your bot token (xxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxx.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx)
SERVER_ID = 000000000000000000   # Your server/guild ID
ROLE_NAME = "Role"              # Name of the role, case sensitive
DAYS_TO_LOOK_BACK = 60          # Number of days to look back for activity
CHANNEL_NAMES = [
    "channel_this_role_uses",
    "shitposts",
    "whatever_etc"
] 


import discord
from discord.ext import commands
from datetime import datetime, timedelta, UTC
import os
from tabulate import tabulate


class User:
    def __init__(self, member):
        self.member = member
        self.display_name = None
        self.message_count = 0
        self.latest_message_date = None

    def update(self, message_date):
        self.message_count += 1
        if self.latest_message_date is None or message_date > self.latest_message_date:
            self.latest_message_date = message_date


print ("--- User activity check ---")
# Bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


# Script to run on successful connection
@bot.event
async def on_ready():
    server = bot.get_guild(SERVER_ID)
    if server is None:
        print("Guild not found!")
        await clean_exit()

    print(f"\nConnected to {server.name} as {bot.user}.")

    role = discord.utils.get(server.roles, name=ROLE_NAME)
    if role is None:
        print(f"Role '{ROLE_NAME}' not found on server, or roles are inacessible to the bot.")
        await clean_exit()

    members_with_role = [member for member in server.members if role in member.roles]
    if len(members_with_role) == 0:
        print("No members with the role '{ROLE_NAME}', or members are inaccessible to the bot.")
        await clean_exit()

    users = {member: User(member) for member in members_with_role}
    for member in members_with_role:
        users[member].display_name = member.display_name
    print(f"Found {len(members_with_role)} members with the role '{ROLE_NAME}'.")
    
    channels = []
    for channel_name in CHANNEL_NAMES:
        channel = discord.utils.get(server.text_channels, name=channel_name)
        if channel is None:
            print(f"Channel '{channel_name}' not found on server, or channels are inaccessible to the bot.")
            await clean_exit()
        channels.append(channel)

    # Verify the bot has access to channels (test fetch 3 messages from each)
    for channel in channels:
        messages = [msg async for msg in channel.history(limit=3)]
        if len(messages) < 3:
            print(f"Failed to fetch messages for '{channel.name}' - bot is probably missing permissions.")
            await clean_exit()

    print("Verified access to channels.  Collecting messages may take a while.")


    # Collect messages
    cutoff_date = datetime.now(UTC) - timedelta(days=DAYS_TO_LOOK_BACK)
    users_with_posts = set()
    for channel in channels:
        print(f"Collecting {channel.name}")
        async for message in channel.history(after=cutoff_date, oldest_first=False, limit=None):
            if message.author in members_with_role:
                users_with_posts.add(message.author)
                users[message.author].update(message.created_at)

    active_users = [users[member] for member in users_with_posts]
    inactive_users = [member for member in members_with_role if member not in users_with_posts]


    # Print results
    print(f"\n--- Active members in '{ROLE_NAME}' ---")
    active_users_sorted = sorted(
        active_users,
        key=lambda user: (-user.message_count, user.member.name.lower())
    )
    now = datetime.now(UTC)
    active_table = [
        [
            user.display_name,
            user.member.name,
            user.message_count,
            (now - user.latest_message_date).days
        ]
        for user in active_users_sorted
    ]
    print(tabulate(active_table, headers=["Display Name", "Username", "Messages", "Latest (days ago)"]))

    print(f"\n--- Inactive members in '{ROLE_NAME}' (no messages in the last {DAYS_TO_LOOK_BACK} days) ---")
    inactive_users_sorted = sorted(
        inactive_users,
        key=lambda member: (member.name.lower(), member.display_name.lower())
    )
    inactive_table = [
        [
            member.display_name,
            member.name
        ]
        for member in inactive_users_sorted
    ]
    print(tabulate(inactive_table, headers=["Display Name", "Username"]))

    await bot.close()

async def clean_exit():
    if bot.is_closed():
        os._exit(0)
    await bot.close()
    os._exit(0)

bot.run(BOT_TOKEN)