import discord
from discord.ext import commands
import aiosqlite
from database import DB_PATH
from utils.checks import is_boss_or_me


class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── owner (ajoute owner bot) ──────────────────────────────────────────
    @commands.command()
    @is_boss_or_me()
    async def owner(self, ctx, *, arg=None):
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
                "INSERT OR IGNORE INTO owners_bot (user_id) VALUES (?)",
                (member.id,)
            )
            await db.commit()
        await ctx.send(f"{member.name} est maintenant owner bot")

    # ── unowner ───────────────────────────────────────────────────────────
    @commands.command()
    @is_boss_or_me()
    async def unowner(self, ctx, *, arg=None):
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
            await db.execute("DELETE FROM owners_bot WHERE user_id = ?", (member.id,))
            await db.commit()
        await ctx.send(f"{member.name} n'est plus owner bot")


async def setup(bot):
    await bot.add_cog(Boss(bot))
