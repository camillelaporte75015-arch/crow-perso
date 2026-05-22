import discord
from discord.ext import commands
from database import get_log_channel
from datetime import datetime
import pytz

PARIS_TZ = pytz.timezone("Europe/Paris")


def now_paris():
    return datetime.now(PARIS_TZ).strftime("%d/%m/%Y à %H:%M:%S")


class Logs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild, log_type: str, content: str):
        ch_id = await get_log_channel(guild.id, log_type)
        if ch_id:
            ch = guild.get_channel(ch_id)
            if ch:
                try:
                    await ch.send(content)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log natif des changements de rôles non déclenchés par une commande du bot."""
        added = set(after.roles) - set(before.roles)
        removed = set(before.roles) - set(after.roles)

        # On cherche l'exécuteur via l'audit log
        executor = None
        try:
            async for entry in after.guild.audit_logs(
                limit=3,
                action=discord.AuditLogAction.member_role_update
            ):
                if entry.target.id == after.id:
                    executor = entry.user
                    break
        except Exception:
            pass

        executor_name = executor.name if executor else "inconnu"

        for role in added:
            await self.send_log(
                after.guild, "addrole",
                f"{executor_name} a ajouté le rôle {role.name} à {after.name}\n"
                f"Date : {now_paris()}"
            )
        for role in removed:
            await self.send_log(
                after.guild, "delrole",
                f"{executor_name} a enlevé le rôle {role.name} à {after.name}\n"
                f"Date : {now_paris()}"
            )


async def setup(bot):
    await bot.add_cog(Logs(bot))
