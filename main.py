import os

from discord_bot import DiscordBot

from helpers import update_db

def main():
    bot = DiscordBot("Extensible bot based on Discord.py's Cogs")

    @bot.event
    async def on_ready():
        # If this is the first launch (Not a reconnection from disconnect)
        if bot.first_launch:
            # Load core modules
            bot.load_extension("core")
            bot.load_extension("accounts")
            bot.load_extension("plugin_manager")
            # Load all available plugins
            for p in os.listdir("plugins"):
                if not p.endswith(".py"):
                    continue

                plugin = p.split(".")[0]

                if plugin == "__pycache__":
                    return

                try:
                    bot.load_extension(f"plugins.{plugin}")
                    bot.plugins.append(plugin)
                    update_db(bot.db, bot.plugins, "plugins")
                except Exception as e:
                    exc = "{0}: {1}".format(type(e).__name__, e)
                    bot.log.warning(f"Failed to load plugin {p}:\n    - {exc}")

            # Set the DiscordBot instance's application info
            bot.app_info = await bot.application_info()

            bot.first_launch = False

        # Print mission control to the console
        bot.log.info("\n".join(bot.mission_control()))

        # Register the servers that the bot has joined
        for server in bot.guilds:
            sid = str(server.id)
            if sid not in bot.servers:
                bot.servers[sid] = {}

        update_db(bot.db, bot.servers, "servers")

    bot.run(bot.config_token)

if __name__ == "__main__":
    main()