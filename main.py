import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
PANEL_API_KEY = os.getenv("PANEL_API_KEY")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

ROLE_ID = 1026653021570089118
VOUCH_CHANNEL_ID = 1026642017238929499
WELCOME_CHANNELS = [1026641924507050065, 1026642017238929499, 1093333229043454006]
REDEEM_POST_CHANNEL = 1369754722973646908
ORDER_NOTIFICATION_CHANNEL = None

valid_keys = {
    "Insta500_z83R4TvnAX38XavgjfVa": True,
    "TestKey_debug": True
}

KEY_PREFIXES = {
    "Insta500_": {"service": 8839, "quantity": 500},
    "insta1000_": {"service": 8839, "quantity": 1000},
    "Insta1000Likes_": {"service": 8650, "quantity": 1000},
    "TiktokLikes1000_": {"service": 1342, "quantity": 1000},
    "Tiktok1000Views_": {"service": 8618, "quantity": 1000},
    "Tiktok1000_": {"service": 9583, "quantity": 1000},
    "TestKey_": {"service": 8618, "quantity": 100}
}

class ServiceSelect(discord.ui.Select):
    def __init__(self, platform):
        self.platform = platform
        options = []
        
        if platform == "Instagram":
            options = [
                discord.SelectOption(label="500 Followers", value="Insta500"),
                discord.SelectOption(label="1000 Followers", value="insta1000"),
                discord.SelectOption(label="1000 Likes", value="Insta1000Likes")
            ]
        elif platform == "TikTok":
            options = [
                discord.SelectOption(label="1000 Likes", value="TiktokLikes1000"),
                discord.SelectOption(label="1000 Views", value="Tiktok1000Views"),
                discord.SelectOption(label="1000 Followers", value="Tiktok1000")
            ]
        
        super().__init__(placeholder=f"Select {platform} Service", options=options)

    async def callback(self, interaction: discord.Interaction):
        service_name = self.values[0]
        await interaction.response.send_modal(RedeemModal(f"{self.platform} - {service_name}"))

class RefillModal(discord.ui.Modal, title="🔄 Request Refill"):
    order_id = discord.ui.TextInput(label="Order ID", placeholder="Enter your order ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        order = self.order_id.value.strip()
        
        payload = {
            "key": PANEL_API_KEY,
            "action": "refill",
            "order": order
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://justanotherpanel.com/api/v2", data=payload) as response:
                data = await response.json()
                if "refill" in data:
                    await interaction.response.send_message(
                        f"✅ Refill request submitted successfully!\n\n"
                        f"📋 **Refill ID: `{data['refill']}`**\n"
                        "⚠️ **IMPORTANT:** Save this Refill ID!\n"
                        "You'll need it to check the status of your refill request.",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ Failed to request refill. Please check your order ID.", ephemeral=True)

class RefillStatusModal(discord.ui.Modal, title="📊 Check Refill Status"):
    refill_id = discord.ui.TextInput(label="Refill ID", placeholder="Enter your refill ID", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        refill = self.refill_id.value.strip()
        
        payload = {
            "key": PANEL_API_KEY,
            "action": "refill_status",
            "refill": refill
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://justanotherpanel.com/api/v2", data=payload) as response:
                data = await response.json()
                if "status" in data:
                    await interaction.response.send_message(
                        f"📊 **Refill Status Update**\n"
                        f"Status: `{data['status']}`\n"
                        f"Refill ID: `{refill}`",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("❌ Failed to get refill status. Please check your refill ID.", ephemeral=True)

class PlatformView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📱 Instagram", style=discord.ButtonStyle.primary)
    async def instagram_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.add_item(ServiceSelect("Instagram"))
        await interaction.response.send_message("Select Instagram Service:", view=view, ephemeral=True)

    @discord.ui.button(label="🎵 TikTok", style=discord.ButtonStyle.primary)
    async def tiktok_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = discord.ui.View()
        view.add_item(ServiceSelect("TikTok"))
        await interaction.response.send_message("Select TikTok Service:", view=view, ephemeral=True)

    @discord.ui.button(label="🔄 Request Refill", style=discord.ButtonStyle.secondary)
    async def refill_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RefillModal())

    @discord.ui.button(label="📊 Refill Status", style=discord.ButtonStyle.secondary)
    async def refill_status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RefillStatusModal())

class RedeemModal(discord.ui.Modal):
    def __init__(self, title):
        super().__init__(title=f"🎁 {title}")
        self.redeem_key = discord.ui.TextInput(label="Your Serial Code", placeholder="Enter your code", required=True)
        self.media_link = discord.ui.TextInput(label="Social Media Link", placeholder="Paste exact link to the post/profile", required=True)
        self.is_public = discord.ui.TextInput(label="Is Your Account Public? (Yes/No)", placeholder="Yes or No", required=True)
        self.add_item(self.redeem_key)
        self.add_item(self.media_link)
        self.add_item(self.is_public)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.redeem_key.value.strip()
        link = self.media_link.value.strip()
        pub = self.is_public.value.strip().lower()

        if pub != "yes":
            await interaction.response.send_message("❌ Your account must be public to use this service.", ephemeral=True)
            return

        if key not in valid_keys:
            await interaction.response.send_message("❌ Invalid or already used key.", ephemeral=True)
            return

        match = next((prefix for prefix in KEY_PREFIXES if key.startswith(prefix)), None)
        if not match:
            await interaction.response.send_message("❌ Invalid key prefix.", ephemeral=True)
            return

        service_info = KEY_PREFIXES[match]
        service_id = service_info["service"]
        quantity = service_info["quantity"]

        payload = {
            "key": PANEL_API_KEY,
            "action": "add",
            "service": service_id,
            "link": link,
            "quantity": quantity
        }

        async with aiohttp.ClientSession() as session:
            async with session.post("https://justanotherpanel.com/api/v2", data=payload) as response:
                data = await response.json()
                if "order" in data:
                    valid_keys.pop(key)
                    order_message = (
                        "✅ Order placed successfully!\n\n"
                        f"📋 **Order ID: `{data['order']}`**\n"
                        "⚠️ **IMPORTANT:** Please save this Order ID!\n"
                        "You will need it to request refills in the future.\n"
                        "Without this ID, you won't be able to request refills for your order."
                    )
                    await interaction.response.send_message(order_message, ephemeral=True)

                    # Send notification to order channel if set
                    if ORDER_NOTIFICATION_CHANNEL:
                        service_name = match.rstrip("_")  # Remove trailing underscore for display
                        notification = (
                            "🛍️ **New Order Placed!**\n"
                            f"Key: `{key}`\n"
                            f"Service: `{service_name}`\n"
                            f"Link: {link}\n"
                            f"Order ID: `{data['order']}`"
                        )
                        try:
                            await ORDER_NOTIFICATION_CHANNEL.send(notification)
                        except Exception as e:
                            print(f"Failed to send order notification: {e}")

                    role = interaction.guild.get_role(ROLE_ID)
                    if role:
                        try:
                            await interaction.user.add_roles(role)
                        except discord.Forbidden:
                            print("Bot couldn't assign the role — skipping.")

                    vouch_channel = interaction.guild.get_channel(VOUCH_CHANNEL_ID)
                    if vouch_channel:
                        try:
                            thank_msg = await vouch_channel.send(
                                f"Thank You <@{interaction.user.id}> for making a purchase! "
                                f"Remember to leave a vouch in this channel!"
                            )
                            await asyncio.sleep(120)
                            await thank_msg.delete()
                        except Exception as e:
                            print(f"Failed to ping vouch channel: {e}")
                else:
                    await interaction.response.send_message("❌ Failed to place order.", ephemeral=True)

@bot.tree.command(name="postredeem", description="Post the platform selection buttons.")
async def postredeem(interaction: discord.Interaction):
    channel = bot.get_channel(REDEEM_POST_CHANNEL)
    if channel:
        await channel.send("Select your platform to redeem your order:", view=PlatformView())
        await interaction.response.send_message("✅ Platform buttons posted.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Channel not found.", ephemeral=True)

@bot.tree.command(name="setorder", description="Set the channel for order notifications")
@app_commands.describe(channel="The channel to send order notifications to")
async def setorder(interaction: discord.Interaction, channel: discord.TextChannel):
    global ORDER_NOTIFICATION_CHANNEL
    ORDER_NOTIFICATION_CHANNEL = channel
    await interaction.response.send_message(
        f"✅ Order notifications will now be sent to {channel.mention}",
        ephemeral=True
    )

@bot.tree.command(name="addkey", description="Add multiple redeemable keys (space-separated).")
@app_commands.describe(keys="The new keys to add (space-separated)")
async def addkey(interaction: discord.Interaction, keys: str):
    added_keys = []
    duplicate_keys = []
    
    key_list = keys.strip().split()
    for key in key_list:
        if key in valid_keys:
            duplicate_keys.append(key)
        else:
            valid_keys[key] = True
            added_keys.append(key)
    
    response = []
    if added_keys:
        response.append(f"✅ Added {len(added_keys)} keys:")
        response.append("```")
        response.append("\n".join(added_keys))
        response.append("```")
    
    if duplicate_keys:
        response.append(f"❗ {len(duplicate_keys)} duplicate keys were skipped:")
        response.append("```")
        response.append("\n".join(duplicate_keys))
        response.append("```")
    
    if not response:
        response.append("❌ No valid keys provided.")
    
    await interaction.response.send_message("\n".join(response), ephemeral=True)

@bot.tree.command(name="listkeys", description="List all currently valid keys.")
async def listkeys(interaction: discord.Interaction):
    if not valid_keys:
        await interaction.response.send_message("No active keys.", ephemeral=True)
    else:
        key_list = "\n".join(valid_keys.keys())
        await interaction.response.send_message(f"🔑 **Active Keys:**\n```\n{key_list}\n```", ephemeral=True)

@bot.event
async def on_member_join(member):
    for channel_id in WELCOME_CHANNELS:
        channel = member.guild.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.send(f"<@{member.id}> has joined!")
                await asyncio.sleep(0.001)
                await msg.delete()
            except Exception as e:
                print(f"Failed to welcome user in channel {channel_id}: {e}")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is online as {bot.user}")

bot.run(TOKEN)
