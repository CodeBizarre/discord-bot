import os
import shutil
import asyncio
import json

from datetime import datetime
from sqlitedict import SqliteDict
from discord import Role, Embed, Message, Emoji, PartialEmoji
from discord.ext import commands
from discord.ext.commands import Context

from discordbot.core.discord_bot import DiscordBot
from discordbot.core.db_tools import update_db
from discordbot.core.time_tools import pretty_datetime

VERSION = "2.4b2"

class Roles(commands.Cog):
    """Add assignable roles to your server.

    This plugin allows you to add roles to a list for users to safely assign themselves.
    There are also time-based roles to give users after they have been in the server a
    certain amount of time.
    """
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "roles"
        self.version = VERSION
        self.backup = True

        db_file = "db/roles.sql"

        try:
            with open("config/config.json") as cfg:
                conf = json.load(cfg)
                self.backup = conf["BackupDB"]
                self.delete_cmds = conf["DeleteCommands"]
        except Exception as error:
            self.bot.log.error(f"Error loading prefix from config file.\n    - {error}")

        if os.path.exists(db_file) and self.backup:
            timestamp = pretty_datetime(datetime.now(), display="FILE")
            try:
                shutil.copyfile(db_file, f"db/backups/roles-{timestamp}.sql")
            except IOError as e:
                error_file = f"db/backups/roles-{timestamp}.sql"
                self.bot.log.error(f"Unable to create file {error_file}\n    - {e}")

        self.sql_db = SqliteDict(
            filename=db_file,
            tablename="roles",
            autocommit=True,
            encode=json.dumps,
            decode=json.loads
        )

        if "servers" not in self.sql_db:
            self.sql_db["servers"] = {}

        self.db = self.sql_db["servers"]

    async def roles_check(self, ctx: Context) -> bool:
        if "roles" in self.db[str(ctx.guild.id)]:
            return True

        await ctx.send(":anger: Server has no assignable roles.")
        return False

    async def delete_invokes(self, invoke: Message, response: Message):
        """Delete invoke and response message if necessary."""
        try:
            remove = self.db[str(invoke.guild.id)]["remove"]
        except KeyError:
            # Server hasn't been set up
            return

        if not remove:
            # Don't delete messages
            return

        await asyncio.sleep(5)

        if not self.delete_cmds:
            try:
                await invoke.delete()
            except Exception as e:
                self.bot.log.error(f"[ROLES] Unable to delete invoke: {e}")

        try:
            await response.delete()
        except Exception as e:
            self.bot.log.error(f"[ROLES] Unable to delete response: {e}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        try:
            del self.db[str(payload.guild_id)]["reacts"][str(payload.message_id)]
            update_db(self.sql_db, self.db, "servers")
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        sid = str(payload.guild_id)
        mid = str(payload.message_id)

        try:
            info = self.db[sid]["reacts"]

            if mid not in info:
                return
            else:
                info = info[mid]

            emoji_name = payload.emoji.name

            for _, data in info.items():
                if data["reaction"] == emoji_name:
                    role = payload.member.guild.get_role(int(data["id"]))

                    await payload.member.add_roles(role, reason="Self-Assign")
                    await payload.member.send(
                        f"You have been the role {role.name} in "
                        f"{payload.member.guild.name}"
                    )
        except Exception as e:
            await payload.member.send(
                ":anger: There was an error assigning the role. Please let the "
                f"server admin know so this can be fixed: `{e}`"
            )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        sid = str(payload.guild_id)
        mid = str(payload.message_id)

        try:
            info = self.db[sid]["reacts"]

            if mid not in info:
                return
            else:
                info = info[mid]

            emoji_name = payload.emoji.name

            for _, data in info.items():
                if data["reaction"] == emoji_name:
                    guild = self.bot.get_guild(payload.guild_id)
                    member = guild.get_member(payload.user_id)
                    role = member.guild.get_role(int(data["id"]))

                    await member.remove_roles(role, reason="Self-Assign")
                    await member.send(
                        f"You no longer have the role {role.name} in "
                        f"{member.guild.name}"
                    )
        except Exception as e:
            await self.bot.get_channel(payload.channel_id).send(
                ":anger: There was an error removing the role. Please let the "
                f"server admin know so this can be fixed: `{e}`"
            )

    @commands.group(aliases=["roles"])
    @commands.guild_only()
    async def role(self, ctx: Context):
        """Base role management commands.

        Running the command without arguments will display the list of available roles
        in the current server.
        """
        if ctx.invoked_subcommand is not None: return

        sid = str(ctx.guild.id)

        if not await self.roles_check(ctx): return

        if len(self.db[sid]["roles"]) > 0:
            embed = Embed(title="Available roles:", color=0x7289DA)

            embed.set_author(name=self.bot.user.name, icon_url=self.bot.app_info.icon_url)

            for name, info in self.db[sid]["roles"].items():
                embed.add_field(name=name.capitalize(), value=info["description"])

            embed.set_footer(
                text="For more information use the `help roles` command."
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(":anger: Server has no self-assignable roles.")

    @role.command(name="add", aliases=["a", "get", "give", "+"])
    @commands.guild_only()
    async def role_add(self, ctx: Context, *, role_name: str):
        """Get a role from the assignable roles list."""
        sid = str(ctx.guild.id)

        response = None

        role_name = role_name.lower()

        if not await self.roles_check(ctx): return

        if role_name not in self.db[sid]["roles"]:
            response = await ctx.send(
                ":anger: That is not an assignable role on this server."
            )
        else:
            role = ctx.guild.get_role(int(self.db[sid]["roles"][role_name]["id"]))

            if role in ctx.author.roles:
                response = await ctx.send(":anger: You already have that role.")
            else:
                await ctx.author.add_roles(role, reason="Self-assign")
                response = await ctx.send(":white_check_mark: Role added!")

        if response is not None:
            await self.delete_invokes(ctx.message, response)

    @role.command(name="remove", aliases=["r", "lose", "take", "-"])
    @commands.guild_only()
    async def role_remove(self, ctx: Context, *, role_name: str):
        """Remove an assignable role from yourself."""
        sid = str(ctx.guild.id)

        response = None

        role_name = role_name.lower()

        if not await self.roles_check(ctx):
            return
        elif role_name not in self.db[sid]["roles"]:
            response = await ctx.send(
                ":anger: That is not an assignable role on this server."
            )
        else:
            role = ctx.guild.get_role(int(self.db[sid]["roles"][role_name]["id"]))

            if role not in ctx.author.roles:
                response = await ctx.send(":anger: You don't have that role.")
            else:
                await ctx.author.remove_roles(role, reason="Self-remove")
                response = await ctx.send(":white_check_mark: Role removed!")

        if response is not None:
            await self.delete_invokes(ctx.message, response)

    @role.group(name="admin")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_admin(self, ctx: Context):
        """Admin commands. Running the command without arguments will show all server
        roles, including command roles, and react roles.
        Server administrator permission required.
        """
        if ctx.invoked_subcommand is not None: return

        sid = str(ctx.guild.id)

        if sid in self.db and len(self.db[sid]["roles"]) > 0:
            embed = Embed(title="Available roles:", color=0x7289DA)

            embed.set_author(name=self.bot.user.name, icon_url=self.bot.app_info.icon_url)

            for name, info in self.db[sid]["roles"].items():
                embed.add_field(name=name, value=info["description"])

            embed.set_footer(
                text="For more information use the `help roles` command."
            )

            await ctx.send(embed=embed)
        else:
            await ctx.send(":anger: This server has no assignable roles.")

    @role_admin.command(name="invokes")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_admin_invokes(self, ctx: Context, remove: bool = None):
        """Manage role commands and confirmation messages being deleted on your server.
        If DeleteCommands is set to True in the bot's config, this will only affect
        the confirmation messages.

        Running the command without arguments will display the current setting.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = { "remove": False }

        if remove is not None:
            self.db[sid]["remove"] = remove

        update_db(self.sql_db, self.db, "servers")
        await ctx.send(f"Remove role invokes: `{self.db[sid]['remove']}`")

    @role_admin.command(name="add")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_admin_add(self, ctx: Context, role_get: Role, *, description: str):
        """Add or update a role on the assignable roles list.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)
        rid = str(role_get.id)
        name = role_get.name.lower()

        if sid not in self.db:
            self.db[sid] = { "roles": {} }
        elif "roles" not in self.db[sid]:
            self.db[sid]["roles"] = {}
        elif name in self.db[sid]["roles"]:
            if self.db[sid]["roles"][name]["id"] != rid:
                await ctx.send(
                    ":anger: There is already a role with the same name in the "
                    "assignable roles list."
                )
            else:
                await ctx.send(":anger: That roles ia already assignable.")

            return

        try:
            self.db[sid]["roles"][name] = {
                "id": rid,
                "description": description
            }

            await ctx.send(f":white_check_mark: Added {name} to assignable roles.")
            update_db(self.sql_db, self.db, "servers")
        except Exception as e:
            await ctx.send(f":anger: Error adding role: {e}")

    @role_admin.command(name="remove")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_admin_remove(self, ctx: Context, *, role_get: Role):
        """Remove a role from the assignable roles list.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)
        name = role_get.name.lower()

        if not await self.roles_check(ctx): return

        if name not in self.db[sid]["roles"]:
            await ctx.send(":anger: That is not an assignable role on this server.")
        else:
            try:
                del self.db[sid]["roles"][name]

                await ctx.send(
                    f":white_check_mark: Removed {role_get.name} from assignable roles."
                )
                update_db(self.sql_db, self.db, "servers")
            except Exception as e:
                await ctx.send(f":anger: Error removing role: {e}")

    @role_admin.group(name="react", aliases=["reacts", "reaction"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_admin_react(self, ctx: Context):
        """Manage reaction-based roles on your server.
        Running the command without arguments will display the list of reaction roles.
        Server administrator permission required.
        """
        if ctx.invoked_subcommand is not None: return

        sid = str(ctx.guild.id)

        if not await self.roles_check(ctx):
            return
        elif "reacts" not in self.db[sid] or len(self.db[sid]["reacts"]) <= 0:
            await ctx.send(":anger: Server has no reaction roles.")
            return

        embed = Embed(name="Reaction Roles", color=0x7289DA)

        for name, data in self.db[sid]["reacts"].items():
            embed.add_field(name=name, value=f"{data} {data}")

        await ctx.send(embed=embed)

    @role_admin_react.command(name="add", aliases=["create"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_react_add(
            self, ctx: Context, message: Message, role_get: Role, *, description: str):
        """Add a new reaction-based role to a message in your server.
        This will start a very quick interactive process for you to select the reaction.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)

        if sid not in self.db:
            self.db[sid] = { "reacts": {} }
        elif "reacts" not in self.db[sid]:
            self.db[sid]["reacts"] = {}

        prompt = await ctx.send("React to this message to set your emoji.")

        try:
            reaction, _ = await ctx.bot.wait_for(
                "reaction_add",
                timeout=20.0,
                check=lambda r, m: m == ctx.message.author and r.message.id == prompt.id
            )
        except asyncio.TimeoutError:
            await ctx.send(":anger: You took too long to react!")
            return

        mid = str(message.id)

        if mid not in self.db[sid]["reacts"]:
            self.db[sid]["reacts"][mid] = {}

        # Convert the reaction emoji to a string if needed
        if isinstance(reaction.emoji, (Emoji, PartialEmoji)):
            reaction = reaction.emoji.name
        else:
            reaction = reaction.emoji

        self.db[sid]["reacts"][mid][role_get.name] = {
            "description": description,
            "id": role_get.id,
            "reaction": reaction,
            "channel": message.channel.id,
            "message": message.id
        }

        update_db(self.sql_db, self.db, "servers")

        await ctx.send(f":white_check_mark: Role {role_get.name} added with {reaction}.")

    @role_admin_react.command(name="remove", aliases=["delete"])
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def role_react_remove(self, ctx: Context, message: Message, *, role_get: Role):
        """Remove a reaction role from a message in your server.
        Server administrator permission required.
        """
        sid = str(ctx.guild.id)
        mid = str(message.id)

        if not await self.roles_check(ctx):
            return
        elif "reacts" not in self.db[sid]:
            await ctx.send(":anger: Server has no reaction roles.")
            return
        elif mid not in self.db[sid]["reacts"]:
            await ctx.send(":anger: That message has no reaction roles.")
            return
        elif role_get.name not in self.db[sid]["reacts"][mid]:
            await ctx.send(":anger: That role is not assignable from that message.")
            return

        try:
            del self.db[sid]["reacts"][mid][role_get.name]
            if len(self.db[sid]["reacts"][mid]) <= 0:
                del self.db[sid]["reacts"][mid]

            await ctx.send(
                f":white_check_mark: {role_get.name} removed from {message.id}"
            )
        except Exception as e:
            await ctx.send(f":anger: Something went wrong: {e}")

def setup(bot):
    bot.add_cog(Roles(bot))

def teardown(bot):
    bot.cogs["Roles"].sql_db.close()
    bot.remove_cog("Roles")
