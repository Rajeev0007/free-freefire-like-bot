import asyncio
import json
import os
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

DEFAULT_API_HOST = "https://free-fire-like1.p.rapidapi.com"
# Store the config next to app.py, regardless of the directory the bot is started from.
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "like_channels.json")
COOLDOWN_SECONDS = 30
# Regions accepted by the self-hosted API (https://github.com/paulafredo/free-fire-like-api).
REGIONS = ["IND", "BR", "US", "SAC", "NA", "BD", "SG", "ME", "PK", "ID", "TH", "VN", "TW", "RU", "EU"]


class LikeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Set API_HOST in .env to use your own API (e.g. http://localhost:5000).
        self.api_host = (os.getenv("API_HOST") or DEFAULT_API_HOST).rstrip("/")
        # The self-hosted API needs a region ("server"). DEFAULT_REGION is used when the user gives none.
        # RapidAPI keeps its original behavior (no region sent unless the user types one).
        self.default_region = ""
        if self.api_host != DEFAULT_API_HOST:
            self.default_region = (os.getenv("DEFAULT_REGION") or "IND").strip().upper()
            print(f"ℹ Using your own API at {self.api_host} (default region: {self.default_region})")
        self.config_data = self.load_config()
        self.cooldowns = {}

        rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.headers = {}
        if rapidapi_key:
            self.headers = {
                'x-rapidapi-key': rapidapi_key,
                'x-rapidapi-host': urlparse(self.api_host).netloc,
            }

    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    def load_config(self):
        default_config = {
            "servers": {}
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    loaded_config.setdefault("servers", {})
                    return loaded_config
            except json.JSONDecodeError:
                print(f"WARNING: The configuration file '{CONFIG_FILE}' is corrupt or empty. Resetting to default configuration.")
        self.save_config(default_config)
        return default_config

    def save_config(self, config_to_save=None):
        data_to_save = config_to_save if config_to_save is not None else self.config_data
        temp_file = CONFIG_FILE + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        os.replace(temp_file, CONFIG_FILE)

    async def check_channel(self, ctx):
        if ctx.guild is None:
            return True
        guild_id = str(ctx.guild.id)
        like_channels = self.config_data["servers"].get(guild_id, {}).get("like_channels", [])
        return not like_channels or str(ctx.channel.id) in like_channels

    @commands.hybrid_command(name="setlikechannel", description="Sets the channels where the /like command is allowed.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.describe(channel="The channel to allow/disallow the /like command in.")
    async def set_like_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        guild_id = str(ctx.guild.id)
        server_config = self.config_data["servers"].setdefault(guild_id, {})
        like_channels = server_config.setdefault("like_channels", [])

        channel_id_str = str(channel.id)

        if channel_id_str in like_channels:
            like_channels.remove(channel_id_str)
            self.save_config()
            await ctx.send(f"✅ Channel {channel.mention} has been **removed** from allowed channels for /like commands. The command is now **disallowed** there.", ephemeral=True)
        else:
            like_channels.append(channel_id_str)
            self.save_config()
            await ctx.send(f"✅ Channel {channel.mention} is now **allowed** for /like commands. The command will **only** work in specified channels if any are set.", ephemeral=True)

    @commands.hybrid_command(name="like", description="Sends likes to a Free Fire player")
    @app_commands.describe(
        uid="Player UID (numbers only, minimum 6 characters)",
        region="Player's server, e.g. IND, BR, US, BD (optional)",
    )
    async def like_command(self, ctx: commands.Context, uid: str, region: Optional[str] = None):
        is_slash = ctx.interaction is not None

        region = (region or self.default_region).strip().upper()
        if region and region not in REGIONS:
            await ctx.reply(f"Unknown region `{region}`. Use one of: {', '.join(REGIONS)}", mention_author=False, ephemeral=True)
            return

        if not await self.check_channel(ctx):
            msg = "This command is not available in this channel. Please use it in an authorized channel."
            await ctx.reply(msg, mention_author=False, ephemeral=True)
            return

        if not uid.isdigit() or len(uid) < 6:
            await ctx.reply("Invalid UID. It must contain only numbers and be at least 6 characters long.", mention_author=False, ephemeral=True)
            return

        user_id = ctx.author.id
        last_used = self.cooldowns.get(user_id)
        if last_used is not None:
            remaining = COOLDOWN_SECONDS - int((datetime.now() - last_used).total_seconds())
            if remaining > 0:
                await ctx.reply(f"Please wait {remaining} seconds before using this command again.", mention_author=False, ephemeral=True)
                return
        self.cooldowns[user_id] = datetime.now()

        try:
            if is_slash:
                # Acknowledge within Discord's 3 second limit; all later replies stay private.
                await ctx.defer(ephemeral=True)
                await self._request_likes(ctx, uid, region, is_slash)
            else:
                async with ctx.typing():
                    await self._request_likes(ctx, uid, region, is_slash)
        except asyncio.TimeoutError:
            await self._send_error_embed(ctx, "Timeout", "The server took too long to respond.", ephemeral=is_slash)
        except aiohttp.ClientError as e:
            print(f"Connection error in like_command: {e}")
            await self._send_api_error(ctx)
        except Exception as e:
            print(f"Unexpected error in like_command: {e}")
            await self._send_error_embed(ctx, "⚡ Critical Error", "An unexpected error occurred. Please try again later.", ephemeral=is_slash)

    @like_command.autocomplete("region")
    async def region_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.upper()
        return [app_commands.Choice(name=r, value=r) for r in REGIONS if r.startswith(current)][:25]

    async def _request_likes(self, ctx: commands.Context, uid: str, region: str, is_slash: bool):
        params = {"uid": uid}
        if region:
            params["server"] = region

        async with self.session.get(f"{self.api_host}/like", params=params, headers=self.headers) as response:
            if response.status == 429:
                await self._send_api_limit_reached(ctx)
                return
            if response.status != 200:
                body = await response.text()
                # The self-hosted API answers 500 {"error": "Player not found"} instead of 404.
                if response.status == 404 or "not found" in body.lower():
                    await self._send_player_not_found(ctx, uid)
                    return
                print(f"API Error: {response.status} - {body}")
                await self._send_api_error(ctx)
                return

            # content_type=None: accept JSON even if the API sends a wrong Content-Type header.
            data = await response.json(content_type=None)

        embed = discord.Embed(
            title="FREE FIRE LIKE",
            color=0x2ECC71 if data.get("status") == 1 else 0xE74C3C,
            timestamp=datetime.now()
        )

        if data.get("status") == 1:
            embed.description = (
                f"\n"
                f"┌  ACCOUNT\n"
                f"├─ NICKNAME: {data.get('player', 'Unknown')}\n"
                f"├─ UID: {uid}\n"
                f"└─ RESULT:\n"
                f"   ├─ ADDED: +{data.get('likes_added', 0)}\n"
                f"   ├─ BEFORE: {data.get('likes_before', 'N/A')}\n"
                f"   └─ AFTER: {data.get('likes_after', 'N/A')}\n"
            )
        else:
            embed.description = "\n┌MAX LIKES\n└─This UID has already received the maximum likes today.\n"

        embed.set_footer(text="DEVELOPED BY THUG")
        embed.description += "\n🔗 JOIN : https://discord.gg/awPm5B3QFg"
        await ctx.send(embed=embed, ephemeral=is_slash)

    async def _send_player_not_found(self, ctx, uid):
        embed = discord.Embed(title="❌ Player Not Found", description=f"The UID {uid} does not exist or is not accessible.", color=0xE74C3C)
        embed.add_field(name="Tip", value="Make sure that:\n- The UID is correct\n- The player is not private", inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_api_limit_reached(self, ctx):
        embed = discord.Embed(
            title="⚠ API Rate Limit Reached",
            description="You have reached the maximum number of requests allowed by the API.",
            color=0xF1C40F
        )
        embed.add_field(
            name="Tip",
            value=(
                "- Wait a few minutes before trying again\n"
                "- Consider upgrading your API plan if this happens often\n"
                "- Avoid sending too many requests in a short time"
            ),
            inline=False
        )
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_api_error(self, ctx):
        embed = discord.Embed(title="⚠ Service Unavailable", description="The Free Fire API is not responding at the moment.", color=0xF39C12)
        embed.add_field(name="Solution", value="Try again in a few minutes.", inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    async def _send_error_embed(self, ctx, title, description, ephemeral=True):
        embed = discord.Embed(title=f"❌ {title}", description=description, color=discord.Color.red(), timestamp=datetime.now())
        embed.set_footer(text="An error occurred.")
        await ctx.send(embed=embed, ephemeral=ephemeral)


async def setup(bot):
    await bot.add_cog(LikeCommands(bot))
