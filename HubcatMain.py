import discord
from discord.ext import commands
import asyncio
from HubcatScrims import ScrimCog
from Prescence import PresenceCog
# Set your token, client ID, and prefix
token = "PLACEHOLDER"
clientid = 1278482879852056627
prefix = "!"


# Set up intents
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.guild_messages = True
intents.message_content = True

# Create the bot instance
client = commands.Bot(command_prefix=prefix, intents=intents, help_command=None, application_id=clientid)

# Event: When the bot is ready
@client.event
async def on_ready():
    print("Bot is online")
    print(f"Logged in as: {client.user} - {client.user.id}")
    try:
        synced_commands = await client.tree.sync()  # Ensure commands are synced
        print(f"Synced {len(synced_commands)} command(s)")
    except Exception as e:
        print(e)

# Event: When the bot joins a guild
@client.event
async def on_guild_join(guild: discord.Guild):  
    await client.tree.sync(guild=guild)

async def load_cogs():
    cogs_to_load = [
        ScrimCog(client),
        PresenceCog
    ]
    for cog in cogs_to_load:
        await client.add_cog(cog)
        print(f"Added commands from {cog.__class__.__name__}:")
        for command in cog.get_commands():
            print(f"- {command.name}")
# Sync commands on startup
async def setup_hook():
    await load_cogs()


client.setup_hook = setup_hook

# Run the bot
client.run(token)
