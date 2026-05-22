import discord
from discord.ext import commands
import asyncio
import aiosqlite

import config
from database import init_db, DB_PATH, is_owner_bot, is_boss

intents = discord.Intents.all()
bot = commands.Bot(
    command_prefix=config.PREFIX,
    intents=intents,
    help_command=None
)

COGS = [
    "cogs.public",
    "cogs.whitelist",
    "cogs.owner",
    "cogs.boss",
    "cogs.me",
    "cogs.logs",
]


# ── Events ─────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await init_db()
    print(f"[OK] Connecté en tant que {bot.user} ({bot.user.id})")
    print(f"[OK] Préfixe : {config.PREFIX}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("Membre introuvable.", delete_after=5)
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("Rôle introuvable.", delete_after=5)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print(f"[ERREUR] {type(error).__name__}: {error}")


@bot.event
async def on_member_update(before, after):
    """
    1. Retire les rôles sys si ajouté par quelqu'un sans autorisation.
    2. Retire les rôles si la limite est dépassée (sauf owner bot+).
    """
    added_roles = set(after.roles) - set(before.roles)
    if not added_roles:
        return

    # Cherche l'exécuteur via audit log
    executor = None
    try:
        async for entry in after.guild.audit_logs(
            limit=5,
            action=discord.AuditLogAction.member_role_update
        ):
            if entry.target.id == after.id:
                executor = entry.user
                break
    except Exception:
        pass

    is_authorized = False
    if executor:
        is_authorized = (
            executor.id == config.MY_ID
            or await is_boss(executor.id)
            or await is_owner_bot(executor.id)
        )

    async with aiosqlite.connect(DB_PATH) as db:
        for role in added_roles:

            # ── Vérification rôle sys ────────────────────────────────────
            async with db.execute(
                "SELECT 1 FROM sys_roles WHERE guild_id = ? AND role_id = ?",
                (after.guild.id, role.id)
            ) as cur:
                is_sys = await cur.fetchone()

            if is_sys and not is_authorized:
                try:
                    await after.remove_roles(role, reason="Rôle sys - non autorisé")
                    print(f"[SYS] {role.name} retiré à {after.name}")
                except Exception as e:
                    print(f"[SYS] Impossible de retirer : {e}")
                continue

            # ── Vérification limite de rôle ──────────────────────────────
            if is_authorized:
                continue  # Les owners peuvent dépasser la limite

            async with db.execute(
                "SELECT max_count FROM limited_roles WHERE guild_id = ? AND role_id = ?",
                (after.guild.id, role.id)
            ) as cur:
                row = await cur.fetchone()

            if row:
                max_count = row[0]
                current_count = len(role.members)
                if current_count > max_count:
                    try:
                        await after.remove_roles(role, reason=f"Limite {max_count} atteinte")
                        print(f"[LIMIT] {role.name} retiré à {after.name} (limite {max_count})")
                    except Exception as e:
                        print(f"[LIMIT] Erreur : {e}")


# ── Lancement ──────────────────────────────────────────────────────────────

async def main():
    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
            print(f"[COG] {cog} chargé")
        await bot.start(config.TOKEN)


asyncio.run(main())
