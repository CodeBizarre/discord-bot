import sys
import os
import shutil

import discord

from os import path

from discord.errors import LoginFailure

from discordbot.core.discord_bot import DiscordBot

from discordbot.core.db_tools import update_db

app_dir = None


def main():
    intents = discord.Intents.default()
    # Requires privileged intent "Members"
    intents.members = True

    bot = DiscordBot("Extensible bot based on Discord.py's Cogs", intents=intents)

    @bot.event
    async def on_ready():
        # If this is the first launch (Not a reconnection from disconnect)
        if bot.first_launch:
            # Check if this is running from a pyinstaller executable
            global app_dir

            if getattr(sys, "frozen", False):
                app_dir = getattr(sys, "_MEIPASS", path.abspath(path.dirname(__file__)))
            else:
                app_dir = False

            bot.log.info(f"_MEIPASS: {app_dir}")

            # Then load core modules first
            bot.load_extension("core.plugins.core")
            bot.load_extension("core.plugins.plugin_manager")

            # Followed by available plugins
            for p in sorted(os.listdir("plugins")):
                if not p.endswith(".py"):
                    continue

                plugin = p.split(".")[0]

                if plugin == "__pycache__":
                    return

                if app_dir:
                    # Copy plugins from the local directory to the temporary directory
                    shutil.copy(f"plugins/{p}", f"{app_dir}/plugins/{p}")

                try:
                    bot.load_extension(f"plugins.{plugin}")
                    bot.plugins.append(plugin)
                    update_db(bot.db, bot.plugins, "plugins")
                except Exception as e:
                    exc = "{0}: {1}".format(type(e).__name__, e)
                    bot.log.warning(f"Failed to load plugin {p}:\n    - {exc}")

            bot.app_info = await bot.application_info()

            bot.first_launch = False

        bot.log.info(bot.mission_control())

        # Ensure all currently joined severs are registered
        for server in bot.guilds:
            sid = str(server.id)
            if sid not in bot.servers:
                bot.servers[sid] = {}

        update_db(bot.db, bot.servers, "servers")

    try:
        bot.run(bot.config_token)
    except LoginFailure as e:
        reason = e.args[0]

        bot.log.error(f"Login failure: {reason}")

        if reason == "Improper token has been passed.":
            bot.log.warning("Please set your token in config/config.json")
    finally:
        global app_dir

        if app_dir and os.path.isdir(app_dir):
            shutil.rmtree(app_dir)


if __name__ == "__main__":
    main()
