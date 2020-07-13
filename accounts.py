from discord import Member, Embed
from discord.ext import commands
from discord.ext.commands import Context

from discord_bot import DiscordBot
from helpers import update_db, get_db_dict

# Function to build an account level embed
async def account_embed(member: Member, level: int) -> Embed:
    tag = f"{member.name}#{member.discriminator}"

    embed = Embed(title=f"{tag}'s Account", color=0x7289DA)
    embed.set_thumbnail(url=str(member.avatar_url))

    embed.add_field(name="Level", value=str(level), inline=False)

    return embed

# Exportable check for a member's account level
def is_level(required=0):
    async def predicate(ctx: Context):
        uid = str(ctx.author.id)
        sid = str(ctx.guild.id)

        db_dict = get_db_dict(f"db/{ctx.bot.database}", "discord-bot", "accounts")

        if sid not in db_dict or uid not in db_dict[sid]:
            return False
        else:
            return db_dict[sid][uid] >= required

    return commands.check(predicate)

class Accounts(commands.Cog):
    """Account system for restricting commands to certain levels."""
    def __init__(self, bot: DiscordBot):
        self.bot = bot
        self.name = "accounts"

    ## Commands
    @commands.group(name="account", aliases=["accounts", "accs"])
    @commands.guild_only()
    async def cmd_account(self, ctx: Context):
        """Base command to manage accounts.

        Running the command without arguments will display your current account level.
        """
        if ctx.invoked_subcommand is None:
            uid = str(ctx.author.id)
            sid = str(ctx.guild.id)

            if sid not in self.bot.accounts:
                # Server hasn't been set up
                await ctx.send(":anger: Server has no accounts.")
                await ctx.send_help("account genesis")
            elif uid not in self.bot.accounts[sid]:
                # User has no account
                await ctx.send(":anger: You do not have an account for this server.")
            else:
                # Send an embed with account information
                embed = await account_embed(ctx.author, self.bot.accounts[sid][uid])

                await ctx.send(embed=embed)

    @cmd_account.command(name="search", aliases=["lookup", "find"])
    @commands.guild_only()
    async def account_search(self, ctx: Context, target: Member):
        """Look up a member's account on the current server."""
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid in self.bot.accounts and uid in self.bot.accounts[sid]:
            embed = await account_embed(target, self.bot.accounts[sid][uid])
            await ctx.send(embed=embed)
        else:
            await ctx.send(":anger: User has no account for this server.")

    @cmd_account.command(name="add", aliases=["create", "new"])
    @commands.guild_only()
    @is_level(10)
    async def account_add(self, ctx: Context, target: Member, level: int):
        """Add an account for a member on the current server.
        Level 10 required.
        """
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in self.bot.accounts:
            # Server hasn't been set up
            await ctx.send(":anger: Server has no accounts.")
            return

        if uid not in self.bot.accounts[sid]:
            self.bot.accounts[sid][uid] = level

            await ctx.send(":white_check_mark: Account created.")
            update_db(self.bot.db, self.bot.accounts, "accounts")
        else:
            await ctx.send(":anger: User already has an account for this server.")

    @cmd_account.command(name="remove", aliases=["delete", "destroy"])
    @commands.guild_only()
    @is_level(10)
    async def account_remove(self, ctx: Context, target: Member):
        """Remove a member's account on the current server.
        Level 10 required.
        """
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in self.bot.accounts:
            await ctx.send(":anger: Server has no accounts.")
            return
        elif uid not in self.bot.accounts[sid]:
            await ctx.send(":anger: User has no account for this server.")
            return
        else:
            self.bot.accounts[sid].pop(uid)

            await ctx.send(":white_check_mark: Account removed.")
            update_db(self.bot.db, self.bot.accounts, "accounts")

    @cmd_account.command(name="update", aliases=["change", "modify"])
    @commands.guild_only()
    @is_level(10)
    async def account_update(self, ctx: Context, target: Member, level: int):
        """Change a member's account level on the current server.
        Level 10 required.
        """
        uid = str(target.id)
        sid = str(ctx.guild.id)

        if sid not in self.bot.accounts:
            await ctx.send(":anger: Server has no accounts.")
            return
        elif uid not in self.bot.accounts[sid]:
            await ctx.send(":anger User has no account for this server.")
            return
        else:
            self.bot.accounts[sid][uid] = level

            update_db(self.bot.db, self.bot.accounts, "accounts")
            await ctx.send(":white_check_mark: Account updated.")

    @cmd_account.command(name="genesis")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def account_admin(self, ctx: Context):
        """Set yourself as an administrator of the current server to create accounts.
        MUST HAVE SERVER ADMINISTRATOR PERMISSION
        """
        uid = str(ctx.author.id)
        sid = str(ctx.guild.id)

        if sid not in self.bot.accounts:
            self.bot.accounts[sid] = {}

        if uid not in self.bot.accounts[sid]:
            self.bot.accounts[sid][uid] = 10

            await ctx.send(":white_check_mark: Admin account created.")
            update_db(self.bot.db, self.bot.accounts, "accounts")
        else:
            await ctx.send(":anger: You already have an account.")

def setup(bot):
    bot.add_cog(Accounts(bot))