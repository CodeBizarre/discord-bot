import sys
import os
import shutil

from os import path

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context, Cog

from discordbot.core.discord_bot import DiscordBot
from discordbot.core.db_tools import update_db
from discordbot.core.plugins.core import is_botmaster

VERSION = "1.1b1"

class PluginManager(Cog):
    """Plugin management system."""
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "plugins"
        self.version = VERSION

    async def bot_check(self, ctx: Context):
        try:
            sid = str(ctx.guild.id)
        except AttributeError:
            # Assume all plugins are available in a direct message
            return True

        # Not a plugin
        if ctx.cog is None:
            return True

        try:
            return ctx.bot.servers[sid][ctx.cog.__class__.__name__.lower()]
        except KeyError:
            # Plugin will default to enabled if not set by a server admin
            return True

    def copy_plugin_if_needed(_, name: str):
        # Check if this is running from a pyinstaller executable
        if getattr(sys, "frozen", False):
            app_dir = getattr(sys, '_MEIPASS', path.abspath(path.dirname(__file__)))
        else:
            app_dir = False

        if app_dir:
            # Copy plugin from the local directory to the temporary directory
            shutil.copy(f"plugins/{name}.py", f"{app_dir}/plugins/{name}.py")

    @commands.group(name="plugins", aliases=["pl", "cogs"])
    async def cmd_plugins(self, ctx: Context):
        """Base command to manage plugins.

        Running the command without arguments will list loaded plugins.
        """
        if ctx.invoked_subcommand is not None:
            return

        embed = Embed(title="Loaded Plugins", color=0x7289DA)
        for i in range(len(self.bot.plugins)):
            plugin = self.bot.plugins[i].capitalize()
            cog = self.bot.cogs[plugin]

            try:
                version = cog.version
            except AttributeError:
                version = "-"

            embed.add_field(
                name=str(i + 1),
                value=f"{plugin} v{version}"
            )

        await ctx.send(embed=embed)

    @cmd_plugins.command(name="load")
    @is_botmaster()
    async def cmd_plugins_load(self, ctx: Context, name: str):
        """Load plugin (Cog). Do not include file extension.
        Botmaster required.
        """
        if name in self.bot.plugins:
            await ctx.send(f":anger: Plugin {name}.py already loaded.")
            return

        if not os.path.isfile(f"plugins/{name}.py"):
            await ctx.send(f":anger: Cannot find plugins/{name}.py")
        else:
            try:
                self.copy_plugin_if_needed(name)

                self.bot.load_extension(f"plugins.{name}")
                self.bot.plugins.append(name)

                update_db(self.bot.db, self.bot.plugins, "plugins")
                await ctx.send(
                    f":white_check_mark: Plugin {name}.py successfully loaded."
                )
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(f":anger: Error loading {name}.py:\n```py\n{exc}\n```")

    @cmd_plugins.command(name="unload")
    @is_botmaster()
    async def cmd_plugins_unload(self, ctx: Context, name: str):
        """Unload plugin (Cog). Do not include file extension.
        Botmaster required.
        """
        if name not in self.bot.plugins:
            await ctx.send(f":anger: Plugin {name}.py is not loaded.")
        else:
            try:
                self.bot.unload_extension(f"plugins.{name}")
                self.bot.plugins.remove(name)

                update_db(self.bot.db, self.bot.plugins, "plugins")
                await ctx.send(
                    f":white_check_mark: Plugin {name}.py successfully unloaded."
                )
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(f":anger: Error unloading {name}.py:\n```py\n{exc}\n```")

    @cmd_plugins.command(name="reload")
    @is_botmaster()
    async def cmd_plugins_reload(self, ctx: Context, name: str):
        """Reload plugin (Cog). Do not include file extension.
        Botmaster required.
        """
        if name not in self.bot.plugins:
            await ctx.send(f":anger: Plugin {name}.py is not loaded.")
        else:
            try:
                self.copy_plugin_if_needed(name)

                self.bot.unload_extension(f"plugins.{name}")
                self.bot.plugins.remove(name)

                update_db(self.bot.db, self.bot.plugins, "plugins")
                await ctx.send(
                    f":white_check_mark: Plugin {name}.py successfully unloaded."
                )

                self.bot.load_extension(f"plugins.{name}")
                self.bot.plugins.append(name)

                update_db(self.bot.db, self.bot.plugins, "plugins")
                await ctx.send(
                    f":white_check_mark: Plugin {name}.py successfully loaded."
                )
            except Exception as e:
                exc = f"{type(e).__name__}, {e}"
                await ctx.send(
                    f":anger: Error reloading {name}.py:\n```py\n{exc}\n```"
                )

    @cmd_plugins.command(name="enable")
    @commands.has_permissions(administrator=True)
    async def cmd_plugins_enable(self, ctx: Context, name: str):
        """Enable a loaded plugin (Cog) on the current server.
        Server administrator permission required.
        """
        if name not in self.bot.plugins:
            # There is a distinction between server-loaded and bot-loaded plugins
            # therefore I do not include the .py extension here purposefully
            await ctx.send(f":anger: No plugin {name} is loaded.")
            return
        else:
            sid = str(ctx.guild.id)

            self.bot.servers[sid][name] = True

            update_db(self.bot.db, self.bot.servers, "servers")
            await ctx.send(f":white_check_mark: Plugin {name} enabled on your server.")

    @cmd_plugins.command(name="disable")
    @commands.has_permissions(administrator=True)
    async def cmd_plugins_disable(self, ctx: Context, name: str):
        """Disable a loaded plugin (Cog) on the current server.
        Server administrator permission required.
        """
        if name not in self.bot.plugins:
            await ctx.send(f":anger: No plugin {name} is loaded.")
            return
        else:
            sid = str(ctx.guild.id)

            self.bot.servers[sid][name] = False

            update_db(self.bot.db, self.bot.servers, "servers")
            await ctx.send(f":white_check_mark: Plugin {name} disabled on your server.")

def setup(bot):
    bot.add_cog(PluginManager(bot))
