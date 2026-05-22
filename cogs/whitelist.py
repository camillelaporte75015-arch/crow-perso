import discord
from discord.ext import commands
import aiosqlite
from datetime import datetime, timedelta
import pytz

from database import DB_PATH, get_log_channel
from utils.checks import is_whitelisted_or_above

PARIS_TZ = pytz.timezone("Europe/Paris")


def now_paris():
    return datetime.now(PARIS_TZ).strftime("%d/%m/%Y à %H:%M:%S")


class Whitelist(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── clear ─────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def clear(self, ctx, *, arg=None):
        await ctx.message.delete()
        if arg is None:
            return

        # clear par mention
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
            to_delete = []
            async for msg in ctx.channel.history(limit=500):
                if msg.author.id == member.id:
                    to_delete.append(msg)
                if len(to_delete) >= 100:
                    break
            if to_delete:
                await ctx.channel.delete_messages(to_delete)
            return

        # clear par nombre
        try:
            count = int(arg.strip())
            await ctx.channel.purge(limit=count)
        except ValueError:
            pass

    # ── mp ────────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def mp(self, ctx, member: discord.Member = None, *, message=None):
        await ctx.message.delete()
        if member is None or message is None:
            await ctx.send("Usage : +mp @membre message", delete_after=5)
            return
        try:
            await member.send(message)
            await ctx.send(f"message envoyé à {member.name}", delete_after=5)
        except discord.Forbidden:
            await ctx.send(f"impossible d'envoyer un message à {member.name}", delete_after=5)

    # ── help ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def help(self, ctx):
        embed = discord.Embed(title="Commandes du bot", color=discord.Color.blurple())

        embed.add_field(name="Publiques", value=(
            "`+ping`\n"
            "`+pic @/id`\n"
            "`+banner @/id`\n"
            "`+snipe`"
        ), inline=False)

        embed.add_field(name="Whitelist", value=(
            "`+clear (nombre/@)`\n"
            "`+mp @membre message`\n"
            "`+mute @/id`\n"
            "`+unmute @/id`\n"
            "`+unmuteall`\n"
            "`+perm`\n"
            "`+lock`\n"
            "`+unlock`\n"
            "`+slowmode (secondes)`\n"
            "`+renew`\n"
            "`+addrole @role @membre`\n"
            "`+delrole @role @membre`\n"
            "`+derank @/id`\n"
            "`+bosslist`\n"
            "`+say texte`\n"
            "`+sync id_categorie`"
        ), inline=False)

        embed.add_field(name="Owner bot", value=(
            "`+allbots`\n"
            "`+vc`\n"
            "`+hide #salon`\n"
            "`+unhide #salon`\n"
            "`+hideall`\n"
            "`+unhideall`\n"
            "`+wl @/id`\n"
            "`+unwl @/id`\n"
            "`+wl list`\n"
            "`+set perm @role`\n"
            "`+del perm @role`\n"
            "`+set perm @role whitelist`\n"
            "`+del perm @role whitelist`\n"
            "`+set perm @role owner`\n"
            "`+del perm @role owner`\n"
            "`+antiderank @role`\n"
            "`+play activité`\n"
            "`+set pic` (pièce jointe)\n"
            "`+set name nom`\n"
            "`+sys @role`\n"
            "`+unsys @role`\n"
            "`+limitrole @role nombre`\n"
            "`+logs type`"
        ), inline=False)

        embed.add_field(name="Boss + moi", value=(
            "`+owner @/id`\n"
            "`+unowner @/id`"
        ), inline=False)

        embed.add_field(name="Moi uniquement", value=(
            "`+boss @/id`\n"
            "`+unboss @/id`"
        ), inline=False)

        await ctx.send(embed=embed)

    # ── mute ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def mute(self, ctx, member: discord.Member = None):
        if member is None and ctx.message.mentions:
            member = ctx.message.mentions[0]
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return
        if member.top_role >= ctx.author.top_role and ctx.author.id != self.bot.owner_id:
            await ctx.send("impossible de mute cet personne")
            return
        try:
            until = discord.utils.utcnow() + timedelta(weeks=1)
            await member.timeout(until, reason=f"Mute par {ctx.author}")
            await ctx.send(f"{member.name} est mute .")
            log_ch_id = await get_log_channel(ctx.guild.id, "mute")
            if log_ch_id:
                ch = ctx.guild.get_channel(log_ch_id)
                if ch:
                    await ch.send(
                        f"{ctx.author.name} a timeout {member.name}\n"
                        f"Date : {now_paris()}"
                    )
        except discord.Forbidden:
            await ctx.send("impossible de mute cet personne")

    # ── unmute ────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def unmute(self, ctx, member: discord.Member = None):
        if member is None and ctx.message.mentions:
            member = ctx.message.mentions[0]
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return
        await member.timeout(None, reason=f"Unmute par {ctx.author}")
        await ctx.send(f"{member.name} est unmute")
        log_ch_id = await get_log_channel(ctx.guild.id, "unmute")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a unto {member.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── unmuteall ─────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def unmuteall(self, ctx):
        count = 0
        for member in ctx.guild.members:
            if member.is_timed_out():
                try:
                    await member.timeout(None)
                    count += 1
                except Exception:
                    pass
        await ctx.send("toutes les personnes peuvent parler")
        log_ch_id = await get_log_channel(ctx.guild.id, "unmuteall")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a unmuteall ({count} membres)\n"
                    f"Date : {now_paris()}"
                )

    # ── perm ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def perm(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT role_id FROM sys_roles WHERE guild_id = ?",
                (ctx.guild.id,)
            ) as cur:
                sys_roles = [r[0] for r in await cur.fetchall()]

            async with db.execute(
                "SELECT role_id FROM whitelist_perms WHERE guild_id = ?",
                (ctx.guild.id,)
            ) as cur:
                wl_perms = [r[0] for r in await cur.fetchall()]

            async with db.execute(
                "SELECT role_id FROM owner_perms WHERE guild_id = ?",
                (ctx.guild.id,)
            ) as cur:
                owner_perms = [r[0] for r in await cur.fetchall()]

        embed = discord.Embed(title="Permissions du serveur", color=discord.Color.blurple())

        if sys_roles:
            embed.add_field(
                name="Rôles sys",
                value=" ".join(f"<@&{r}>" for r in sys_roles),
                inline=False
            )

        roles_sorted = sorted(ctx.guild.roles, reverse=True)
        roles_text = "\n".join(
            f"<@&{r.id}>" for r in roles_sorted if not r.is_default()
        )
        if roles_text:
            embed.add_field(name="Rôles (ordre)", value=roles_text[:1024], inline=False)

        if wl_perms:
            embed.add_field(
                name="Perms whitelist",
                value=" ".join(f"<@&{r}>" for r in wl_perms),
                inline=False
            )
        if owner_perms:
            embed.add_field(
                name="Perms owner",
                value=" ".join(f"<@&{r}>" for r in owner_perms),
                inline=False
            )

        await ctx.send(embed=embed)

    # ── lock ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def lock(self, ctx):
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = False
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send("les membres ne peuvent plus parler ici")
        log_ch_id = await get_log_channel(ctx.guild.id, "lock")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a lock le salon {ctx.channel.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── unlock ────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def unlock(self, ctx):
        ow = ctx.channel.overwrites_for(ctx.guild.default_role)
        ow.send_messages = True
        await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send("les membres peuvent à nouveau parler")
        log_ch_id = await get_log_channel(ctx.guild.id, "unlock")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a unlock le salon {ctx.channel.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── slowmode ──────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def slowmode(self, ctx, time: int = 0):
        await ctx.channel.edit(slowmode_delay=time)
        if time == 0:
            await ctx.send("slowmode désactivé")
        else:
            await ctx.send(f"slowmode {time}s activé")

    # ── renew ─────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def renew(self, ctx):
        channel = ctx.channel
        name = channel.name
        position = channel.position
        category = channel.category
        topic = getattr(channel, "topic", None)

        new_channel = await channel.clone(name=name, reason=f"Renew par {ctx.author}")
        await new_channel.edit(position=position)
        await channel.delete()
        await new_channel.send("les membres peuvent à nouveau parler")

        log_ch_id = await get_log_channel(ctx.guild.id, "renew")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a renew le salon {name}\n"
                    f"Date : {now_paris()}"
                )

    # ── addrole ───────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def addrole(self, ctx, role: discord.Role = None, member: discord.Member = None):
        # support reply
        if member is None and ctx.message.reference:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = ref.author
        if role is None or member is None:
            await ctx.send("Usage : +addrole @role @membre", delete_after=5)
            return
        await member.add_roles(role)
        await ctx.send("1 rôle a été ajouté à un membre")
        log_ch_id = await get_log_channel(ctx.guild.id, "addrole")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a ajouté le rôle {role.name} à {member.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── delrole ───────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def delrole(self, ctx, role: discord.Role = None, member: discord.Member = None):
        if member is None and ctx.message.reference:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            member = ref.author
        if role is None or member is None:
            await ctx.send("Usage : +delrole @role @membre", delete_after=5)
            return
        await member.remove_roles(role)
        await ctx.send("1 rôle a été supprimé à un membre")
        log_ch_id = await get_log_channel(ctx.guild.id, "delrole")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a enlevé le rôle {role.name} à {member.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── derank ────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def derank(self, ctx, member: discord.Member = None):
        if member is None and ctx.message.mentions:
            member = ctx.message.mentions[0]
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute(
                "SELECT role_id FROM antiderank_roles WHERE guild_id = ?",
                (ctx.guild.id,)
            ) as cur:
                protected = {r[0] for r in await cur.fetchall()}

        to_remove = [
            r for r in member.roles
            if not r.is_default() and r.id not in protected
        ]
        if to_remove:
            await member.remove_roles(*to_remove)

        await ctx.send(f"{member.name} a été derank")

        log_ch_id = await get_log_channel(ctx.guild.id, "derank")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                perms_text = ", ".join(r.name for r in to_remove) or "aucun"
                await ch.send(
                    f"{ctx.author.name} a derank {member.name}\n"
                    f"Permissions retiré : {perms_text}\n"
                    f"Date : {now_paris()}"
                )

    # ── bosslist ──────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def bosslist(self, ctx):
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id FROM bosses") as cur:
                rows = await cur.fetchall()
        if not rows:
            await ctx.send("Aucun boss enregistré.")
            return
        lines = []
        for (uid,) in rows:
            m = ctx.guild.get_member(uid)
            lines.append(f"<@{uid}> / {uid}" if m else str(uid))
        embed = discord.Embed(
            title="Boss list",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    # ── say ───────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def say(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

    # ── sync ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_whitelisted_or_above()
    async def sync(self, ctx, category_id: int = None):
        if category_id is None:
            await ctx.send("Précise l'ID de la catégorie.", delete_after=5)
            return
        category = ctx.guild.get_channel(category_id)
        if not isinstance(category, discord.CategoryChannel):
            await ctx.send("Catégorie introuvable.", delete_after=5)
            return
        for channel in category.channels:
            await channel.edit(sync_permissions=True)
        await ctx.send("tout les salons de cet catégorie on été synchronisé")


async def setup(bot):
    await bot.add_cog(Whitelist(bot))
