import discord
from discord.ext import commands
import os

# ==================== CONFIGURATION ====================
TOKEN = os.getenv("TOKEN")  # Set this in Railway environment variables

ALLOWED_ROLE_IDS = [
    1512766885379313704,  # ← Add your allowed role ID(s) here
]

# ==================== IN-MEMORY DATA (Railway-safe) ====================
# Railway's filesystem is ephemeral — data.json resets on redeploy.
# We store settings in memory. To persist across restarts, use a database
# or store values as Railway environment variables instead.
bot_data = {
    "button_label": os.getenv("BUTTON_LABEL", "Garden"),
    "list_text": os.getenv("LIST_TEXT", "1\nhttps://discord.gg/example"),
    "embed_title": os.getenv("EMBED_TITLE", "🌱 Garden Servers"),
    "embed_description": os.getenv("EMBED_DESCRIPTION", "Click the button below to see all invites.")
}

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


def has_permission(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    user_role_ids = [role.id for role in member.roles]
    return any(role_id in ALLOWED_ROLE_IDS for role_id in user_role_ids)


class DynamicButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Garden", style=discord.ButtonStyle.green, custom_id="dynamic_button")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(bot_data["list_text"], ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    # Register persistent view
    bot.add_view(DynamicButton())
    # Sync slash commands — REQUIRED for /commands to appear in Discord
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    text = """
**Commands:**
`/help` — Show this message

**Admin Commands** (Owner + Allowed Roles):
`/setup` — Edit button name, list, embed title & description
`/post` — Post the embed with the button

**Normal Users:**
Click the button on the embed to view the list.
"""
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="setup", description="Edit button name, list, and embed")
async def setup(interaction: discord.Interaction):
    # Get the member object to check roles properly
    member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
    if member is None or not has_permission(member):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    class EditModal(discord.ui.Modal, title="Edit Settings"):
        button_name = discord.ui.TextInput(
            label="Button Name",
            default=bot_data["button_label"],
            max_length=80
        )
        list_text = discord.ui.TextInput(
            label="Your Numbered List",
            style=discord.TextStyle.long,
            default=bot_data["list_text"]
        )
        embed_title = discord.ui.TextInput(
            label="Embed Title (optional)",
            default=bot_data.get("embed_title", ""),
            required=False
        )
        embed_description = discord.ui.TextInput(
            label="Embed Description (optional)",
            default=bot_data.get("embed_description", ""),
            required=False,
            style=discord.TextStyle.long
        )

        async def on_submit(self, modal_interaction: discord.Interaction):
            bot_data["button_label"] = self.button_name.value
            bot_data["list_text"] = self.list_text.value
            bot_data["embed_title"] = self.embed_title.value or "🌱 Garden Servers"
            bot_data["embed_description"] = self.embed_description.value or "Click the button below to see all invites."
            await modal_interaction.response.send_message("✅ Settings saved!", ephemeral=True)

    await interaction.response.send_modal(EditModal())


@bot.tree.command(name="post", description="Post the embed with button (Admin only)")
async def post(interaction: discord.Interaction):
    member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
    if member is None or not has_permission(member):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    embed = discord.Embed(
        title=bot_data.get("embed_title", "🌱 Garden Servers"),
        description=bot_data.get("embed_description", "Click the button below to see all invites."),
        color=discord.Color.green()
    )

    view = DynamicButton()
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Embed posted!", ephemeral=True)


if TOKEN is None:
    raise ValueError("❌ TOKEN environment variable is not set! Add it in Railway → Variables.")

bot.run(TOKEN)
