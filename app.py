import os
import sys
import threading
import traceback

import aiohttp
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from flask import Flask
from waitress import serve

load_dotenv()

TOKEN = os.getenv("TOKEN")
PORT = int(os.environ.get("PORT", 10000))
HTTP_TIMEOUT_SECONDS = 15

app = Flask(__name__)
bot_name = "None"


@app.route('/')
def home():
    return f"Bot {bot_name} is active"


def run_flask():
    # waitress is a production WSGI server and works on Windows, Linux and macOS.
    serve(app, host="0.0.0.0", port=PORT)


extensions = [
    "cogs.likeCommands"
]


class Seemu(commands.Bot):
    def __init__(self, command_prefix: str, intents: discord.Intents, **kwargs):
        super().__init__(command_prefix=command_prefix, intents=intents, **kwargs)
        self.session = None

    async def setup_hook(self) -> None:
        # Shared HTTP session for all cogs. Without a timeout aiohttp waits up to 5 minutes.
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        )

        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"✅ {ext} loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load {ext}: {e}")
                traceback.print_exc()

        await self.tree.sync()
        print("✔ All cogs loaded")
        self.update_activity_task.start()

    async def on_ready(self):
        global bot_name
        server_count = len(self.guilds)
        activity = discord.Game(name=f"Sharing likes on {server_count} servers")
        await self.change_presence(activity=activity)
        bot_name = f"{self.user}"
        print(f"\n🔗 Connected as {bot_name}")
        print(f"🌐 Flask running on port {PORT}\n")

    @tasks.loop(minutes=5)
    async def update_activity_task(self):
        try:
            server_count = len(self.guilds)
            activity = discord.Game(name=f"Sharing likes on {server_count} servers !! ")
            await self.change_presence(activity=activity)
            print(f"Activity updated: sharing likes on {server_count} servers")
        except Exception as e:
            print(f"⚠ Error while updating activity: {e}")
            traceback.print_exc()

    @update_activity_task.before_loop
    async def before_update_activity_task(self):
        await self.wait_until_ready()
        print("Bot ready, starting activity update loop.")

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handler for prefix and hybrid (slash) commands."""
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingPermissions):
            msg = "❌ You need to be an administrator to use this command."
        elif isinstance(error, commands.NoPrivateMessage):
            msg = "❌ This command can only be used in a server."
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = f"⚠ Missing required argument: `{error.param.name}`."
        elif isinstance(error, (commands.BadArgument, commands.ChannelNotFound)):
            msg = f"⚠ Invalid argument: {error}"
        else:
            print(f"Unhandled error: {error}")
            traceback.print_exception(type(error), error, error.__traceback__)
            msg = "⚠ An unexpected error occurred. [1214]"

        try:
            # Context.send picks the right method (reply, interaction response or followup).
            await ctx.send(msg, ephemeral=True)
        except discord.HTTPException:
            pass


if __name__ == "__main__":
    if not TOKEN:
        print("❌ TOKEN not found. Create a .env file with TOKEN=your_discord_bot_token")
        sys.exit(1)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Intents.all() needs every privileged intent enabled in the Developer Portal,
    # otherwise login fails. The bot only needs Message Content for prefix commands (!like).
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Seemu(command_prefix="!", intents=intents)
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("❌ Invalid Discord token")
        sys.exit(1)
    except discord.errors.PrivilegedIntentsRequired:
        print("❌ Enable 'Message Content Intent' for your bot in the Discord Developer Portal (Bot tab).")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        sys.exit(0)
    except Exception as e:
        print(f"⚠ Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
