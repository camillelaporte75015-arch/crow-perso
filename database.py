import aiosqlite

DB_PATH = "data/bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bosses (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS owners_bot (
                user_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS snipe (
                guild_id    INTEGER,
                channel_id  INTEGER,
                author      TEXT,
                content     TEXT,
                deleted_at  TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                guild_id    INTEGER,
                log_type    TEXT,
                channel_id  INTEGER,
                PRIMARY KEY (guild_id, log_type)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sys_roles (
                guild_id INTEGER,
                role_id  INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS limited_roles (
                guild_id  INTEGER,
                role_id   INTEGER,
                max_count INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS antiderank_roles (
                guild_id INTEGER,
                role_id  INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS whitelist_perms (
                guild_id INTEGER,
                role_id  INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS owner_perms (
                guild_id INTEGER,
                role_id  INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        await db.commit()


# ── Helpers ────────────────────────────────────────────────────────────────

async def is_whitelisted(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def is_boss(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM bosses WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def is_owner_bot(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM owners_bot WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None


async def get_log_channel(guild_id: int, log_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id FROM logs WHERE guild_id = ? AND log_type = ?",
            (guild_id, log_type)
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else None


async def set_log_channel(guild_id: int, log_type: str, channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO logs (guild_id, log_type, channel_id) VALUES (?, ?, ?)",
            (guild_id, log_type, channel_id)
        )
        await db.commit()
