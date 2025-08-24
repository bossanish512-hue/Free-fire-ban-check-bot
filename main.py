import discord
from discord.ext import commands
import aiohttp
import json
import os
from datetime import datetime, timedelta, timezone

intents = discord.Intents.default()
intents.message_content = True

# Bot with prefix ! and /
bot = commands.Bot(command_prefix=commands.when_mentioned_or("!", "/"), intents=intents, help_command=None)

# File to save channel config
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

config = load_config()

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")

# -------------------------
# Admin Commands
# -------------------------
@bot.command()
@commands.has_permissions(administrator=True)
async def setbancheckchannel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    config[guild_id] = {"channel_id": channel.id}
    save_config(config)
    await ctx.send(f"✅ Ban check channel has been set to {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def removebancheckchannel(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in config:
        del config[guild_id]
        save_config(config)
        await ctx.send("✅ Ban check channel has been removed.")
    else:
        await ctx.send("⚠️ No ban check channel was set.")

# -------------------------
# Check Command
# -------------------------
@bot.command()
async def check(ctx, uid: str = None):
    guild_id = str(ctx.guild.id)
    if guild_id not in config:
        return await ctx.send("⚠️ Please set a ban check channel first using `!setbancheckchannel #channel`")

    allowed_channel_id = config[guild_id]["channel_id"]
    if ctx.channel.id != allowed_channel_id:
        allowed_channel = ctx.guild.get_channel(allowed_channel_id)
        return await ctx.send(f"❌ You can’t use this command here. Please use it in {allowed_channel.mention}.")

    if not uid or not uid.isdigit():
        return await ctx.send("❌ Use: !check <uid>")

    loading_msg = await ctx.send("🔍 Checking ban status...")

    url = f"http://raw.thug4ff.com/check_ban/{uid}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return await loading_msg.edit(content="❌ Failed to fetch data from the API.")
                data = await response.json()
        except Exception as e:
            return await loading_msg.edit(content=f"❌ Error: {e}")

    if not isinstance(data, dict) or "status" not in data:
        return await loading_msg.edit(content="❌ Invalid response from API.")

    user_data = data.get("data", data)

    def safe_value(val):
        if val is None or str(val).strip() == "" or str(val).lower() in ("n/a", "no data"):
            return "No Data"
        return str(val)

    is_banned = int(user_data.get("is_banned", 0)) == 1
    nickname = safe_value(user_data.get("nickname") or user_data.get("name") or "No Data")
    player_uid = safe_value(user_data.get("id") or user_data.get("uid") or "No Data")
    region = safe_value(user_data.get("region") or user_data.get("country") or "No Data")

    last_login_raw = user_data.get("last_login") or user_data.get("last_seen")
    if last_login_raw and isinstance(last_login_raw, int):
        try:
            dt_login = datetime.fromtimestamp(last_login_raw, timezone.utc) + timedelta(hours=5, minutes=45)
            last_login = dt_login.strftime("%Y-%m-%d %I:%M %p")
        except Exception:
            last_login = "No Data"
    else:
        last_login = "No Data"

    nepal_time = datetime.now(timezone.utc) + timedelta(hours=5, minutes=45)
    time_str = nepal_time.strftime("%I:%M %p")

    color = discord.Color.red() if is_banned else discord.Color.green()
    embed = discord.Embed(color=color)

    if is_banned:
        reason = "This account was confirmed for using cheats."
        period = user_data.get("period")
        period_unit = user_data.get("period_unit")
        if period and isinstance(period, int):
            unit = period_unit if period_unit else "month"
            unit_str = unit if period == 1 else unit + "s"
            suspension = f"more than {period} {unit_str}"
        else:
            suspension = user_data.get("suspension") or "No Data"

        embed.title = "🚫 BANNED ACCOUNT"
        embed.description = (
            f"**┌ ACCOUNT BAN INFO**\n"
            f"**├─ Status**: Banned\n"
            f"**├─ Reason**: {reason}\n"
            f"**├─ Suspension Duration**: {suspension}\n"
            f"**├─ Nickname**: {nickname}\n"
            f"**├─ Player UID**: `{player_uid}`\n"
            f"**├─ Last Login**: {last_login}\n"
            f"**└─ Region**: {region}"
        )
        embed.set_image(url="https://i.ibb.co/wFxTy8TZ/banned.gif")
    else:
        embed.title = "✅ CLEAN ACCOUNT"
        embed.description = (
            f"**┌ ACCOUNT BASIC INFO**\n"
            f"**├─ Status**: Clean\n"
            f"**├─ Nickname**: {nickname}\n"
            f"**├─ Player UID**: `{player_uid}`\n"
            f"**├─ Last Login**: {last_login}\n"
            f"**└─ Region**: {region}"
        )
        embed.set_image(url="https://i.ibb.co/Kx1RYVKZ/notbanned.gif")

    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    embed.set_footer(text=f"DEVELOPED BY M8N TEAM | Today at {time_str}")

    await loading_msg.edit(content=None, embed=embed)

# -------------------------
# Error Handler
# -------------------------
@setbancheckchannel.error
async def setbancheckchannel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Only admins can use this command.")

@removebancheckchannel.error
async def removebancheckchannel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Only admins can use this command.")

# -------------------------
# Run Bot
# -------------------------
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN is not set in environment variables!")
    else:
        bot.run(TOKEN)
