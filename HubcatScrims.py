import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import pytz
import json
import os

class ScrimView(discord.ui.View):
    def __init__(self, scrim_cog, message_id):
        super().__init__(timeout=None)
        self.scrim_cog = scrim_cog
        self.message_id = message_id

    @discord.ui.button(label="Main", style=discord.ButtonStyle.primary, emoji="👥")
    async def main_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.scrim_cog.handle_button_click(interaction, self.message_id, '👥')

    @discord.ui.button(label="Substitute", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def substitute_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.scrim_cog.handle_button_click(interaction, self.message_id, '🛡️')

    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.scrim_cog.handle_remove_click(interaction, self.message_id)

class ScrimCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scrims_file = 'scrims.json'
        self.main_limit = 10
        self.reserve_limit = 5
        self.timezone_map = {
            'UK': 'Europe/London',
            'NY': 'America/New_York',
            'Dallas': 'America/Chicago',
            'California': 'America/Los_Angeles'
        }
        self.scrims = self.load_scrims()

    def load_scrims(self):
        if os.path.exists(self.scrims_file):
            with open(self.scrims_file, 'r') as f:
                return json.load(f)
        return {}

    def save_scrims(self):
        with open(self.scrims_file, 'w') as f:
            json.dump(self.scrims, f, indent=4)

    @app_commands.command(name="scrim", description="Create a scrim event.")
    @app_commands.describe(
        time="The time you want the scrim, in hhmm format.",
        timezone="The timezone for the scrim."
    )
    @app_commands.choices(
        timezone=[
            app_commands.Choice(name='UK', value='UK'),
            app_commands.Choice(name='NY', value='NY'),
            app_commands.Choice(name='Dallas', value='Dallas'),
            app_commands.Choice(name='California', value='California')
        ]
    )
    async def scrim(self, interaction: discord.Interaction, time: int, timezone: str):
        try:
            if timezone not in self.timezone_map:
                return await interaction.response.send_message('Invalid timezone selected. [UK/NY/Dallas/California]', ephemeral=True)

            # Check user roles
            allowed_roles = {1135869809880477797, 1013777500947611789}
            user_roles = {role.id for role in interaction.user.roles}
            if not allowed_roles.intersection(user_roles):
                return await interaction.response.send_message('You do not have permission to run this command.', ephemeral=True)

            # Get the specific parent channel by ID
            parent_channel_id = 1219946930948538408
            parent_channel = self.bot.get_channel(parent_channel_id)
            if not parent_channel or not isinstance(parent_channel, discord.TextChannel):
                return await interaction.response.send_message('The specified parent channel is not valid.', ephemeral=True)

            # Create a thread under the specified parent channel
            thread_name = f'scrim-{time}-{timezone}'
            thread = await parent_channel.create_thread(name=thread_name, auto_archive_duration=60, type=discord.ChannelType.public_thread)

            # Convert provided time to Unix timestamp in the selected timezone
            tz = pytz.timezone(self.timezone_map[timezone])
            now = datetime.now(tz)
            provided_time = datetime.strptime(str(time), '%H%M').replace(year=now.year, month=now.month, day=now.day)
            localized_time = tz.localize(provided_time)
            delay = (localized_time - now).total_seconds()

            # Create the embed for the main channel
            embed = discord.Embed(title='Breachy Scrim!', description=f"{interaction.user.mention} has created a scrim for: <t:{int(localized_time.timestamp())}:R>", color=discord.Color.green())
            embed.add_field(name='Main', value='No signups yet', inline=False)
            embed.add_field(name='Reserves', value='No signups yet', inline=False)
            embed.add_field(name='Timezone', value=timezone, inline=False)
            embed.set_thumbnail(url="https://i.imgur.com/JAPtsMl.png")
            message = await parent_channel.send(embed=embed, view=ScrimView(self, thread.id))
            await message.pin()  # Pin the embed message

            # Create a similar embed for the thread
            thread_embed = discord.Embed(title='Scrim Details', description=f"{interaction.user.mention} has created a scrim for: <t:{int(localized_time.timestamp())}:R>", color=discord.Color.blue())
            thread_embed.add_field(name='Main Signups', value='No signups yet', inline=False)
            thread_embed.add_field(name='Reserve Signups', value='No signups yet', inline=False)
            thread_embed.add_field(name='Timezone', value=timezone, inline=False)
            thread_message = await thread.send(embed=thread_embed)
            await thread_message.pin()  # Pin the thread message

            # Notify in the original channel
            await interaction.response.send_message(f'Scrim thread created: {thread.mention}', ephemeral=True)
            
            # Notify users when scrim starts
            await asyncio.sleep(delay)
            await self.notify_users(thread, thread.id)



            # Update or create the scrim information
            scrim_data = self.scrims.get(str(thread.id), {})
            scrim_data.update({
                'main_reactions': [],
                'sub_reactions': [],
                'notified': False,
                'timezone': timezone
            })
            self.scrims[str(thread.id)] = scrim_data
            self.save_scrims()

        except Exception as e:
            print(e)

    async def handle_button_click(self, interaction, message_id, emoji):
        user = interaction.user
        scrim_data = self.scrims.get(str(message_id), {})

        if 'main_reactions' not in scrim_data:
            scrim_data['main_reactions'] = []

        if 'sub_reactions' not in scrim_data:
            scrim_data['sub_reactions'] = []

        if emoji == '👥':
            if user.id in scrim_data['sub_reactions']:
                scrim_data['sub_reactions'].remove(user.id)
        elif emoji == '🛡️':
            if user.id in scrim_data['main_reactions']:
                scrim_data['main_reactions'].remove(user.id)

        if emoji == '👥':
            if user.id not in scrim_data['main_reactions'] and len(scrim_data['main_reactions']) < self.main_limit:
                scrim_data['main_reactions'].append(user.id)
                await interaction.response.send_message(f"Signed you up as main {emoji}.", ephemeral=True)
            else:
                await interaction.response.send_message('Main section is full or you are already signed up.', ephemeral=True)
        elif emoji == '🛡️':
            if user.id not in scrim_data['sub_reactions'] and len(scrim_data['sub_reactions']) < self.reserve_limit:
                scrim_data['sub_reactions'].append(user.id)
                await interaction.response.send_message(f"Signed you up as sub {emoji}.", ephemeral=True)
            else:
                await interaction.response.send_message('Reserve section is full or you are already signed up.', ephemeral=True)

        self.scrims[str(message_id)] = scrim_data
        self.save_scrims()
        await self.update_embeds(interaction.message, scrim_data)

    async def handle_remove_click(self, interaction, message_id):
        user = interaction.user
        scrim_data = self.scrims.get(str(message_id), {})

        if user.id in scrim_data.get('main_reactions', []):
            scrim_data['main_reactions'].remove(user.id)
            await interaction.response.send_message("You have been removed from the main list.", ephemeral=True)
        elif user.id in scrim_data.get('sub_reactions', []):
            scrim_data['sub_reactions'].remove(user.id)
            await interaction.response.send_message("You have been removed from the sub list.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not in the list.", ephemeral=True)

        self.scrims[str(message_id)] = scrim_data
        self.save_scrims()
        await self.update_embeds(interaction.message, scrim_data)

    async def update_embeds(self, message, scrim_data):
        embed = message.embeds[0]
        main_signups = [f"<@{user_id}>" for user_id in scrim_data.get('main_reactions', [])]
        reserve_signups = [f"<@{user_id}>" for user_id in scrim_data.get('sub_reactions', [])]

        embed.set_field_at(0, name=f"Main - 👥 ({len(scrim_data.get('main_reactions', []))}/{self.main_limit})", value='\n'.join(main_signups) or 'No signups yet', inline=False)
        embed.set_field_at(1, name=f"Reserves - 🛡️ ({len(scrim_data.get('sub_reactions', []))}/{self.reserve_limit})", value='\n'.join(reserve_signups) or 'No signups yet', inline=False)

        await message.edit(embed=embed)

        # Update the thread embed as well
        thread = discord.utils.get(message.channel.threads, name='scrim-discussion')
        if thread:
            thread_embed = discord.Embed(title='Scrim Details', description=f"Scrim is starting at <t:{int(datetime.now(pytz.timezone(self.timezone_map[scrim_data['timezone']])).timestamp())}:R>", color=discord.Color.blue())
            thread_embed.add_field(name='Main Signups', value='\n'.join(main_signups) or 'No signups yet', inline=False)
            thread_embed.add_field(name='Reserve Signups', value='\n'.join(reserve_signups) or 'No signups yet', inline=False)
            thread_embed.add_field(name='Timezone', value=scrim_data.get('timezone', 'Unknown'), inline=False)
            await thread.send(embed=thread_embed)

    async def notify_users(self, thread, message_id):
        scrim_data = self.scrims.get(str(message_id), {})
        main_users = [self.bot.get_user(user_id) for user_id in scrim_data.get('main_reactions', [])]
        reserve_users = [self.bot.get_user(user_id) for user_id in scrim_data.get('sub_reactions', [])]

        # Notify main users
        if main_users:
            for user in main_users:
                try:
                    await user.send(f'The scrim you signed up for is starting soon in {thread.name}.')
                except discord.HTTPException:
                    pass

            await thread.send(f'{", ".join(user.mention for user in main_users)} - Scrim is starting now!')

        # Notify reserve users
        if reserve_users:
            await asyncio.sleep(300)  # Wait 5 minutes before notifying reserves
            for user in reserve_users:
                try:
                    await user.send(f'The scrim you signed up started 5 minutes ago in {thread.mention}. Go check if they need someone!')
                except discord.HTTPException:
                    pass

            await thread.send(f'{", ".join(user.mention for user in reserve_users)} - Scrim is starting now!')

        # Set 'notified' to True after notifying users
        scrim_data['notified'] = True
        self.scrims[str(message_id)] = scrim_data
        self.save_scrims()


