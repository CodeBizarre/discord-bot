import os
import shutil
import json

from datetime import datetime
from sqlitedict import SqliteDict
from discord import Role, Member, Embed
from discord.ext import commands
from discord.ext.commands import Context
from main import is_level
from helpers import pretty_datetime, update_db

VERSION = "1.0.0b1"

# Get the database set up
db_file = "db/roles.sql"
backup = True

try:
    with open("config/config.json") as cfg:
        backup = json.load(cfg)["BackupDB"]
except Exception as error:
    print(f"Error loading prefix from configuration file.\n    - {error}")

if os.path.exists(db_file) and backup:
    timestamp = pretty_datetime(datetime.now(), display="FILE")
    try:
        shutil.copyfile(db_file, f"db/backups/roles-{timestamp}.sql")
    except IOError as e:
        print(
            f"""
            Unable to create file db/backups/roles-{timestamp}.sql:\n
            {e}
            """
        )

sql_db = SqliteDict(
    filename=db_file,
    tablename="roles",
    autocommit=True,
    encode=json.dumps,
    decode=json.loads
)

if "servers" not in sql_db:
    sql_db["servers"] = {}

db = sql_db["servers"]

class Roles(commands.Cog):
    """Add assignable roles to your server.

    This plugin allows you to add roles to a list for users to safely assign themselves.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.name = "roles"
        self.app_info = None

    @commands.group(aliases=["roles"])
    @commands.guild_only()
    async def role(self, ctx: Context):
        """Role related commands.

        Running the command without arguments will display the list of available roles
        in the current server.
        """
        if ctx.invoked_subcommand is None:
            sid = str(ctx.message.guild.id)

            if sid in db and len(db[sid]) > 0:
                if self.app_info is None:
                    self.app_info = await self.bot.application_info()

                embed = Embed(title="Available roles:", color=0x00ffff)
                embed.set_author(
                    name=self.bot.user.name,
                    icon_url=self.app_info.icon_url
                )

                for r, d in db[sid].items():
                    embed.add_field(
                        name=r,
                        value=d["description"],
                        inline=True
                    )

                embed.set_footer(
                    text="For more information use the `help roles` command."
                )

                await ctx.send(embed=embed)
            else:
                await ctx.send("This server has no assignable roles.")

    @role.command(name="get", aliases=["g"])
    @commands.guild_only()
    async def role_get(self, ctx: Context, *, role_name: str):
        """Get a role."""
        sid = str(ctx.message.guild.id)

        if sid not in db:
            await ctx.send("This server has no assignable roles.")
            return

        if role_name not in db[sid]:
            await ctx.send("That is not an assignable role on this server.")
        else:
            role = ctx.guild.get_role(int(db[sid][role_name]["id"]))
            await ctx.author.add_roles(role, reason="Self-assign")
            await ctx.send("Role added!")

    @role.command(name="lose", aliases=["l"])
    @commands.guild_only()
    async def role_lose(self, ctx: Context, *, role_name: str):
        """Lose a role."""
        sid = str(ctx.message.guild.id)

        if sid not in db:
            await ctx.send("This server has no assignable roles.")
            return

        if role_name not in db[sid]:
            await ctx.send("That is not an assignable role on this server.")
        else:
            role = ctx.guild.get_role(int(db[sid][role_name]["id"]))
            await ctx.author.remove_roles(role, reason="Self-remove")
            await ctx.send("Role removed!")

    @role.command(name="add", aliases=["a"])
    @commands.guild_only()
    @is_level(10)
    async def role_add(self, ctx: Context, role_get: Role, *, description: str):
        """Add/update an assignable role to the server."""
        sid = str(ctx.message.guild.id)
        rid = str(role_get.id)
        name = role_get.name

        if sid not in db:
            db[sid] = {}

        try:
            role_info = {
                "id": rid,
                "description": description
            }
            db[sid][name] = role_info
            update_db(sql_db, db, "servers")
            await ctx.send(f"Added {name} to assignable roles.")
        except Exception as e:
            await ctx.send(f"Error adding role: {e}")

    @role.command(name="remove", aliases=["r"])
    @commands.guild_only()
    @is_level(10)
    async def role_remove(self, ctx: Context, *, role_get: Role):
        """Remove an assignable role from the server."""
        sid = str(ctx.message.guild.id)

        if sid not in db:
            await ctx.send("There are no assignable roles on this server.")
            return

        if role_get.name not in db[sid]:
            await ctx.send("That is not an assignable role on this server.")
        else:
            try:
                del db[sid][role_get.name]
                update_db(sql_db, db, "servers")
                await ctx.send(f"Removed {role_get.name} from assignable roles.")
            except Exception as e:
                await ctx.send(f"Error removing role: {e}")

def setup(bot):
    bot.add_cog(Roles(bot))
