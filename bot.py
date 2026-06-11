import discord
from discord.ext import commands
import json
import os

# ==================== CONFIGURATION ====================
TOKEN = os.getenv("TOKEN")   # Token is loaded from environment variables (safer)

ALLOWED_ROLE_IDS = [
    123456789012345678,   # ← Add your allowed role ID(s) here
]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {
        "button_label": "Garden",
        "list_text": "1\nhttps://discord.gg/example",
        "embed_title": "🌱 Garden Servers",
        "embed_description": "Click the button below to see all invites."
    }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def has_permission(member: discord.Member) -> bool:
    if member.guild.owner_id == member.id:
        return True
    user_role_ids = [role.id for role in member.roles]
    return any(role_id in ALLOWED_ROLE_IDS for role_id in user_role_ids)

class DynamicButton(discord.ui.View):
    def __init__(self, label: str):
        super().__init__(timeout=None)
        self.label = label

    @discord.ui.button(label="Temp", style=discord.ButtonStyle.green, custom_id="dynamic_button")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        button.label = data["button_label"]
        await interaction.response.send_message(data["list_text"], ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    data = load_data()
    bot.add_view(DynamicButton(data["button_label"]))

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
    if not has_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    data = load_data()

    class EditModal(discord.ui.Modal, title="Edit Settings"):
        button_name = discord.ui.TextInput(label="Button Name", default=data["button_label"], max_length=80)
        list_text = discord.ui.TextInput(label="Your Numbered List", style=discord.TextStyle.long, default=data["list_text"])
        embed_title = discord.ui.TextInput(label="Embed Title (optional)", default=data.get("embed_title", ""), required=False)
        embed_description = discord.ui.TextInput(label="Embed Description (optional)", default=data.get("embed_description", ""), required=False, style=discord.TextStyle.long)

        async def on_submit(self, modal_interaction: discord.Interaction):
            new_data = {
                "button_label": self.button_name.value,
                "list_text": self.list_text.value,
                "embed_title": self.embed_title.value or data.get("embed_title", "🌱 Garden Servers"),
                "embed_description": self.embed_description.value or data.get("embed_description", "Click the button below to see all invites.")
            }
            save_data(new_data)
            await modal_interaction.response.send_message("✅ Settings saved!", ephemeral=True)

    await interaction.response.send_modal(EditModal())

@bot.tree.command(name="post", description="Post the embed with button (Admin only)")
async def post(interaction: discord.Interaction):
    if not has_permission(interaction.user):
        await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
        return

    data = load_data()
    embed = discord.Embed(
        title=data.get("embed_title", "🌱 Garden Servers"),
        description=data.get("embed_description", "Click the button below to see all invites."),
        color=discord.Color.green()
    )
    view = DynamicButton(data["button_label"])
    await interaction.channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Embed posted!", ephemeral=True)

bot.run(TOKEN)
