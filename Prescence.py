import discord
from discord.ext import commands, tasks
import json
import os
import random

class PresenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.presence_file = 'presence.json'
        self.update_presence_task.start()

    @tasks.loop(minutes=10)
    async def update_presence_task(self):
        """Load the JSON file and update the bot's presence every 10 minutes."""
        if os.path.exists(self.presence_file):
            with open(self.presence_file, 'r') as file:
                statuses = json.load(file)
            
            if statuses:
                status = random.choice(statuses)
                await self.bot.change_presence(activity=discord.Game(name=status))
                print(f"Updated presence to: {status}")
            else:
                print("No statuses found in the JSON file.")
        else:
            print(f"{self.presence_file} not found.")

    @update_presence_task.before_loop
    async def before_update_presence_task(self):
        """Wait until the bot is ready before starting the task."""
        await self.bot.wait_until_ready()
