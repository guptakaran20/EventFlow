import asyncpg
import asyncio

async def run():
    conn = await asyncpg.connect('postgresql://eventflow:eventflow@localhost:15432/postgres')
    await conn.execute('CREATE DATABASE eventflow_test')
    await conn.close()

asyncio.run(run())
