import discord
from discord.ext import commands
import aiosqlite
from database import DB_PATH
from datetime import datetime
import pytz

PARIS_TZ = pytz.timezone("Europe/Paris")


class Public(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── ping ──────────────────────────────────────────────────────────────
    @commands.command()
    async def ping(self, ctx):
        await ctx.message.delete()
        await ctx.send("nique ta mère")

    # ── pic ───────────────────────────────────────────────────────────────
    @commands.command()
    async def pic(self, ctx, *, arg=None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            try:
                uid = int(arg.strip())
                member = ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
            except Exception:
                pass
        if member is None:
            member = ctx.author

        embed = discord.Embed(color=discord.Color.blurple())
        embed.set_image(url=member.display_avatar.url)
        embed.set_footer(text=f"Avatar de {member.name}")
        await ctx.send(embed=embed)

    # ── banner ────────────────────────────────────────────────────────────
    @commands.command()
    async def banner(self, ctx, *, arg=None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            try:
                uid = int(arg.strip())
                member = ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
            except Exception:
                pass
        if member is None:
            member = ctx.author

        user = await self.bot.fetch_user(member.id)
        if user.banner:
            embed = discord.Embed(color=discord.Color.blurple())
            embed.set_image(url=user.banner.url)
            embed.set_footer(text=f"Bannière de {member.name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member.name} n'a pas de bannière.")

    # ── snipe ─────────────────────────────────────────────────────────────
    @commands.command()
    async def snipe(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT author, content, deleted_at FROM snipe "
                "WHERE channel_id = ? ORDER BY rowid DESC LIMIT 1",
                (ctx.channel.id,)
            ) as cur:
                row = await cur.fetchone()

        if not row:
            await ctx.send("Aucun message supprimé récemment dans ce salon.")
            return

        author, content, deleted_at = row
        embed = discord.Embed(description=content, color=discord.Color.red())
        embed.set_author(name=author)
        embed.set_footer(text=f"Supprimé le {deleted_at}")
        await ctx.send(embed=embed)

    # ── listener : stocke le dernier message supprimé ─────────────────────
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.content:
            return
        now = datetime.now(PARIS_TZ).strftime("%d/%m/%Y à %H:%M:%S")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM snipe WHERE channel_id = ?",
                (message.channel.id,)
            )
            await db.execute(
                "INSERT INTO snipe (guild_id, channel_id, author, content, deleted_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (message.guild.id, message.channel.id,
                 str(message.author), message.content, now)
            )
            await db.commit()


async def setup(bot):
    await bot.add_cog(Public(bot))
