import discord
from discord.ext import commands
import aiosqlite
import aiohttp
from datetime import datetime
import pytz

from database import DB_PATH, get_log_channel, set_log_channel
from utils.checks import is_owner_or_above, is_boss_or_me
import config

PARIS_TZ = pytz.timezone("Europe/Paris")

LOG_TYPES = [
    "mute", "unmute", "unmuteall",
    "addrole", "delrole",
    "lock", "unlock",
    "renew", "wl", "unwl", "derank"
]


def now_paris():
    return datetime.now(PARIS_TZ).strftime("%d/%m/%Y à %H:%M:%S")


async def resolve_member(ctx, arg: str):
    arg = arg.strip().replace("<@", "").replace(">", "").replace("!", "")
    try:
        uid = int(arg)
        return ctx.guild.get_member(uid) or await ctx.guild.fetch_member(uid)
    except Exception:
        return discord.utils.find(lambda m: m.name.lower() == arg.lower(), ctx.guild.members)


async def resolve_role(ctx, arg: str):
    arg = arg.strip().replace("<@&", "").replace(">", "")
    try:
        rid = int(arg)
        return ctx.guild.get_role(rid)
    except Exception:
        return discord.utils.find(lambda r: r.name.lower() == arg.lower(), ctx.guild.roles)


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── allbots ───────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def allbots(self, ctx):
        bots = [m for m in ctx.guild.members if m.bot]
        lines = [f"<@{b.id}> / {b.id}" for b in bots]
        embed = discord.Embed(
            title="Bots du serveur",
            description="\n".join(lines) or "Aucun bot",
            color=discord.Color.blurple()
        )
        await ctx.send(embed=embed)

    # ── vc ────────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def vc(self, ctx):
        guild = ctx.guild
        total = guild.member_count
        online = sum(
            1 for m in guild.members
            if m.status != discord.Status.offline and not m.bot
        )
        in_vc = sum(1 for m in guild.members if m.voice is not None)
        streaming = sum(
            1 for m in guild.members
            if m.voice and m.voice.self_stream
        )
        embed = discord.Embed(
            title=f"({total}) statistiques",
            color=discord.Color.blurple()
        )
        embed.add_field(name="membre", value=str(total), inline=False)
        embed.add_field(name="en ligne", value=str(online), inline=False)
        embed.add_field(name="en vocal", value=str(in_vc), inline=False)
        embed.add_field(name="en stream", value=str(streaming), inline=False)
        await ctx.send(embed=embed)

    # ── hide ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def hide(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send(f"le salon {channel.name} n'est plus visible par les membres")

    # ── unhide ────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def unhide(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel
        ow = channel.overwrites_for(ctx.guild.default_role)
        ow.view_channel = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
        await ctx.send(f"le salon {channel.name} est maintenant visible par les membres")

    # ── hideall ───────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def hideall(self, ctx):
        count = 0
        for channel in ctx.guild.channels:
            try:
                ow = channel.overwrites_for(ctx.guild.default_role)
                ow.view_channel = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
                count += 1
            except Exception:
                pass
        await ctx.send(f"{count} sont invisibles pour les membres")

    # ── unhideall ─────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def unhideall(self, ctx):
        for channel in ctx.guild.channels:
            try:
                ow = channel.overwrites_for(ctx.guild.default_role)
                ow.view_channel = True
                await channel.set_permissions(ctx.guild.default_role, overwrite=ow)
            except Exception:
                pass
        await ctx.send("tout les salons sont maintenant visible par les membres")

    # ── wl ────────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def wl(self, ctx, *, arg=None):
        # +wl list
        if arg and arg.strip().lower() == "list":
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id FROM whitelist") as cur:
                    rows = await cur.fetchall()
            if not rows:
                await ctx.send("Aucune personne whitelistée.")
                return
            lines = []
            for (uid,) in rows:
                m = ctx.guild.get_member(uid)
                lines.append(f"<@{uid}> / {uid}" if m else str(uid))
            embed = discord.Embed(
                title="whitelist :",
                description="\n".join(lines),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

        # +wl @membre ou id
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            member = await resolve_member(ctx, arg)

        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)",
                (member.id,)
            )
            await db.commit()
        await ctx.send(f"{member.name} est maintenant whitelist")

        log_ch_id = await get_log_channel(ctx.guild.id, "wl")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a whitelist {member.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── unwl ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def unwl(self, ctx, *, arg=None):
        member = None
        if ctx.message.mentions:
            member = ctx.message.mentions[0]
        elif arg:
            member = await resolve_member(ctx, arg)
        if member is None:
            await ctx.send("Précise un membre.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM whitelist WHERE user_id = ?", (member.id,))
            await db.commit()
        await ctx.send(f"{member.name} n'est plus whitelist")

        log_ch_id = await get_log_channel(ctx.guild.id, "unwl")
        if log_ch_id:
            ch = ctx.guild.get_channel(log_ch_id)
            if ch:
                await ch.send(
                    f"{ctx.author.name} a unwhitelist {member.name}\n"
                    f"Date : {now_paris()}"
                )

    # ── set ───────────────────────────────────────────────────────────────
    # Gère : +set perm @role
    #        +set perm @role whitelist
    #        +set perm @role owner
    #        +set pic
    #        +set name nom
    @commands.command(name="set")
    @is_owner_or_above()
    async def set_cmd(self, ctx, sub: str = None, *, args: str = None):
        if sub is None:
            return

        # ── set pic ──────────────────────────────────────────────────────
        if sub.lower() == "pic":
            if not ctx.message.attachments:
                await ctx.send("Attache une image.", delete_after=5)
                return
            url = ctx.message.attachments[0].url
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            await self.bot.user.edit(avatar=data)
            await ctx.send("ma photo de profil a bien été modifié")
            return

        # ── set name ─────────────────────────────────────────────────────
        if sub.lower() == "name":
            if not args:
                await ctx.send("Précise un nom.", delete_after=5)
                return
            await ctx.guild.me.edit(nick=args.strip())
            await ctx.send("mon pseudo a bien été changé")
            return

        # ── set perm ─────────────────────────────────────────────────────
        if sub.lower() == "perm":
            if not args:
                await ctx.send("Usage : +set perm @role  ou  +set perm @role whitelist/owner", delete_after=5)
                return

            parts = args.strip().split()
            # Détecte si la cible est whitelist ou owner (dernier mot)
            target_type = None
            role_str = args.strip()

            if parts[-1].lower() in ("whitelist", "owner"):
                target_type = parts[-1].lower()
                role_str = " ".join(parts[:-1]).strip()

            # Résout le rôle
            role = None
            if ctx.message.role_mentions:
                role = ctx.message.role_mentions[0]
            else:
                role = await resolve_role(ctx, role_str)

            if role is None:
                await ctx.send("Rôle introuvable.", delete_after=5)
                return

            # +set perm @role whitelist
            if target_type == "whitelist":
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "INSERT OR IGNORE INTO whitelist_perms (guild_id, role_id) VALUES (?, ?)",
                        (ctx.guild.id, role.id)
                    )
                    await db.commit()
                await ctx.send(f"le rôle {role.name} a été ajouté aux perms whitelist .")
                return

            # +set perm @role owner
            if target_type == "owner":
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "INSERT OR IGNORE INTO owner_perms (guild_id, role_id) VALUES (?, ?)",
                        (ctx.guild.id, role.id)
                    )
                    await db.commit()
                await ctx.send(f"le rôle {role.name} a été ajouté aux perms owner .")
                return

            # +set perm @role (sans cible = perm Discord sur le rôle)
            await ctx.send(f"perm ajoutée au rôle {role.name} .")

    # ── del ───────────────────────────────────────────────────────────────
    # Gère : +del perm @role
    #        +del perm @role whitelist
    #        +del perm @role owner
    @commands.command(name="del")
    @is_owner_or_above()
    async def del_cmd(self, ctx, sub: str = None, *, args: str = None):
        if sub is None or sub.lower() != "perm" or not args:
            await ctx.send("Usage : +del perm @role  ou  +del perm @role whitelist/owner", delete_after=5)
            return

        parts = args.strip().split()
        target_type = None
        role_str = args.strip()

        if parts[-1].lower() in ("whitelist", "owner"):
            target_type = parts[-1].lower()
            role_str = " ".join(parts[:-1]).strip()

        role = None
        if ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        else:
            role = await resolve_role(ctx, role_str)

        if role is None:
            await ctx.send("Rôle introuvable.", delete_after=5)
            return

        if target_type == "whitelist":
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "DELETE FROM whitelist_perms WHERE guild_id = ? AND role_id = ?",
                    (ctx.guild.id, role.id)
                )
                await db.commit()
            await ctx.send(f"la permissions {role.name} a bien été enlevé .")
            return

        if target_type == "owner":
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "DELETE FROM owner_perms WHERE guild_id = ? AND role_id = ?",
                    (ctx.guild.id, role.id)
                )
                await db.commit()
            await ctx.send(f"la permissions {role.name} a bien été enlevé .")
            return

        # +del perm @role (perm Discord)
        await ctx.send(f"la permissions {role.name} a bien été enlevé .")

    # ── antiderank ────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def antiderank(self, ctx, role: discord.Role = None):
        if role is None and ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        if role is None:
            await ctx.send("Précise un rôle.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO antiderank_roles (guild_id, role_id) VALUES (?, ?)",
                (ctx.guild.id, role.id)
            )
            await db.commit()
        await ctx.send(f"le role {role.name} ne peut plus être enlever lors d'un derank")

    # ── play ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def play(self, ctx, *, activity: str = None):
        if not activity:
            await ctx.send("Précise une activité.", delete_after=5)
            return
        await self.bot.change_presence(activity=discord.Game(name=activity))
        await ctx.send(f"je joue maintenant a {activity}")

    # ── sys ───────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def sys(self, ctx, role: discord.Role = None):
        if role is None and ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        if role is None:
            await ctx.send("Précise un rôle.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR IGNORE INTO sys_roles (guild_id, role_id) VALUES (?, ?)",
                (ctx.guild.id, role.id)
            )
            await db.commit()
        await ctx.send(f"{role.name} est maintenant un role sys")

    # ── unsys ─────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def unsys(self, ctx, role: discord.Role = None):
        if role is None and ctx.message.role_mentions:
            role = ctx.message.role_mentions[0]
        if role is None:
            await ctx.send("Précise un rôle.", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM sys_roles WHERE guild_id = ? AND role_id = ?",
                (ctx.guild.id, role.id)
            )
            await db.commit()
        await ctx.send(f"{role.name} n'est maintenant plus sys")

    # ── limitrole ─────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def limitrole(self, ctx, role: discord.Role = None, limit: int = None):
        if role is None or limit is None:
            await ctx.send("Usage : +limitrole @role nombre", delete_after=5)
            return
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO limited_roles (guild_id, role_id, max_count) VALUES (?, ?, ?)",
                (ctx.guild.id, role.id, limit)
            )
            await db.commit()
        await ctx.send(f"une limitrole de {limit} pour le role {role.name}")

    # ── logs ──────────────────────────────────────────────────────────────
    @commands.command()
    @is_owner_or_above()
    async def logs(self, ctx, log_type: str = None):
        if log_type is None:
            await ctx.send(
                f"Types disponibles : {', '.join(LOG_TYPES)}",
                delete_after=10
            )
            return
        log_type = log_type.lower()
        if log_type not in LOG_TYPES:
            await ctx.send(
                f"Type inconnu. Disponibles : {', '.join(LOG_TYPES)}",
                delete_after=10
            )
            return
        existing = await get_log_channel(ctx.guild.id, log_type)
        if existing:
            ch = ctx.guild.get_channel(existing)
            ch_name = ch.name if ch else str(existing)
            await ctx.send(f"les logs {log_type} sont déjà dans le salon {ch_name} .")
            return
        await set_log_channel(ctx.guild.id, log_type, ctx.channel.id)
        await ctx.send(f"ce salon est maintenant le logs {log_type}")


async def setup(bot):
    await bot.add_cog(Owner(bot))
