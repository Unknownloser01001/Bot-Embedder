python
import discord
from discord.ext import commands
import json
import os
import sys

# ==================== CONFIGURATION ====================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ ERROR: TOKEN environment variable is not set.")
    sys.exit(1)

ALLOWED_ROLE_IDS = [
    1512766885379313704,  # ← Add your allowed role ID(s) here
]

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

DEFAULT_DATA = {
    "button_label": "Garden",
    "list_text": "1\nhttps://discord.gg/example",
    "embed_title": "🌱 Garden Servers",
    "embed_description": "Click the button below to see all invites.",
}


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"⚠️ Warning: Could not read {DATA_FILE} ({e}). Using defaults.")
    return DEFAULT_DATA.copy()


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def has_permission(user) -> bool:
    if not isinstance(user, discord.Member):
        return False
    if user.guild.owner_id == user.id:
        return True
    user_role_ids = {role.id for role in user.roles}
    return bool(user_role_ids & set(ALLOWED_ROLE_IDS))


class DynamicButton(discord.ui.View):
    def __init__(self, label: str):
        super().__init__(timeout=None)
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "dynamic_button":
                item.label = label

    @discord.ui.button(label="...", style=discord.ButtonStyle.green, custom_id="dynamic_button")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        await interaction.response.send_message(data["list_text"], ephemeral=True)


@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    data = load_data()
    bot.add_view(DynamicButton(data["button_label"]))
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    text = (
        "**Commands:**\n"
        "`/help` — Show this message\n\n"
        "**Admin Commands** (Owner + Allowed Roles):\n"
        "`/setup` — Edit button name, list, embed title & description\n"
        "`/post` — Post the embed with the button\n\n"
        "**Normal Users:**\n"
        "Click the button on the embed to view the list."
    )
    await interaction.response.send_message(text, ephemeral=True)


@bot.tree.command(name="setup", description="Edit button name, list, and embed")
async def setup(interaction: discord.Interaction):
    if not interaction.guild or not has_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    data = load_data()

    class EditModal(discord.ui.Modal, title="Edit Settings"):
        button_name = discord.ui.TextInput(
            label="Button Name",
            default=data["button_label"],
            max_length=80,
        )
        list_text = discord.ui.TextInput(
            label="Your Numbered List",
            style=discord.TextStyle.long,
            default=data["list_text"],
        )
        embed_title = discord.ui.TextInput(
            label="Embed Title (optional)",
            default=data.get("embed_title", ""),
            required=False,
        )
        embed_description = discord.ui.TextInput(
            label="Embed Description (optional)",
            default=data.get("embed_description", ""),
            required=False,
            style=discord.TextStyle.long,
        )

        async def on_submit(self, modal_interaction: discord.Interaction):
            try:
                new_data = {
                    "button_label": self.button_name.value,
                    "list_text": self.list_text.value,
                    "embed_title": self.embed_title.value or data.get("embed_title", DEFAULT_DATA["embed_title"]),
                    "embed_description": self.embed_description.value or data.get("embed_description", DEFAULT_DATA["embed_description"]),
                }
                save_data(new_data)
                await modal_interaction.response.send_message("✅ Settings saved!", ephemeral=True)
            except Exception as e:
                print(f"❌ Error saving data: {e}")
                if not modal_interaction.response.is_done():
                    await modal_interaction.response.send_message(
                        "❌ Failed to save settings. Please try again.", ephemeral=True
                    )

    await interaction.response.send_modal(EditModal())


@bot.tree.command(name="post", description="Post the embed with button (Admin only)")
async def post(interaction: discord.Interaction):
    if not interaction.guild or not has_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    if interaction.channel is None:
        await interaction.response.send_message("❌ Cannot determine the channel.", ephemeral=True)
        return

    data = load_data()

    embed = discord.Embed(
        title=data.get("embed_title", DEFAULT_DATA["embed_title"]),
        description=data.get("embed_description", DEFAULT_DATA["embed_description"]),
        color=discord.Color.green(),
    )

    view = DynamicButton(data["button_label"])
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)
    await interaction.followup.send("✅ Embed posted!", ephemeral=True)


bot.run(TOKEN)
