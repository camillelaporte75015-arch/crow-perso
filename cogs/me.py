import discord
from discord.ext import commands
import aiosqlite
from database import DB_PATH
from utils.checks import is_me


class Me(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── boss ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_me()
    async def boss(self, ctx, *, arg=None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            arg = arg.strip().replace("<@", "").replace(">", "").replace("!", "")
            try:
                uid = int(arg)
                member = ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
            except Exception:
                pass
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO bosses (user_id) VALUES (?)",
                (member.id,)
            )
            await db.commit()
        await ctx.send(f"{member.name} est maintenant boss")

    # ── unboss ────────────────────────────────────────────────────────────
    @commands.command()
    @is_me()
    async def unboss(self, ctx, *, arg=None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            arg = arg.strip().replace("<@", "").replace(">", "").replace("!", "")
            try:
                uid = int(arg)
                member = ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
            except Exception:
                pass
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM bosses WHERE user_id = ?", (member.id,))
            await db.commit()
        await ctx.send(f"{member.name} n'est plus boss")


async def setup(bot):
    await bot.add_cog(Me(bot))
