from discord.ext import commands
import config
import database


def is_me():
    async def predicate(ctx):
        return ctx.author.id == config.MY_ID
    return commands.check(predicate)


def is_boss_or_me():
    async def predicate(ctx):
        if ctx.author.id == config.MY_ID:
            return True
        return await database.is_boss(ctx.author.id)
    return commands.check(predicate)


def is_owner_or_above():
    async def predicate(ctx):
        if ctx.author.id == config.MY_ID:
            return True
        if await database.is_boss(ctx.author.id):
            return True
        return await database.is_owner_bot(ctx.author.id)
    return commands.check(predicate)


def is_whitelisted_or_above():
    async def predicate(ctx):
        if ctx.author.id == config.MY_ID:
            return True
        if await database.is_boss(ctx.author.id):
            return True
        if await database.is_owner_bot(ctx.author.id):
            return True
        return await database.is_whitelisted(ctx.author.id)
    return commands.check(predicate)
