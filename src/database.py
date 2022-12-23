import aiosqlite
import os


class StatsTable:
    def __init__(self, database_path):
        self.database_path = database_path

    async def create(self):
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("CREATE TABLE stats(user_id int, film_name varchar(4096))")
            await database.commit()

    async def update(self, user_id, film_name):
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("INSERT INTO stats (user_id, film_name) VALUES (?, ?)", (user_id, film_name,))
            await database.commit()

    async def get(self, user_id):
        async with aiosqlite.connect(self.database_path) as database:
            async with database.execute(f"SELECT film_name, count(*) "
                                        f"FROM stats "
                                        f"WHERE user_id = {user_id} "
                                        f"GROUP BY film_name") as cursor:
                return [row async for row in cursor]


class HistoryTable:
    def __init__(self, database_path):
        self.database_path = database_path

    async def create(self):
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("CREATE TABLE history (user_id int, query varchar(4096))")
            await database.commit()

    async def update(self, user_id, query):
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute("INSERT INTO history (user_id, query) VALUES (?, ?)", (user_id, query,))
            await database.commit()

    async def get(self, user_id):
        async with aiosqlite.connect(self.database_path) as database:
            async with database.execute(f"SELECT (query)"
                                        f"FROM history "
                                        f"WHERE user_id = {user_id}") as cursor:
                return [row[0] async for row in cursor]


class CinemaDatabaseHandler:
    def __init__(self, database_path):
        self.database_path = database_path
        self.stats_table = StatsTable(self.database_path)
        self.history_table = HistoryTable(self.database_path)

    def exists(self):
        return os.path.exists(self.database_path)

    async def create_database(self):
        open(self.database_path, 'a').close()
        await self.stats_table.create()
        await self.history_table.create()

    async def update_history(self, user_id, query):
        await self.history_table.update(user_id, query)

    async def update_stats(self, user_id, film_name):
        await self.stats_table.update(user_id, film_name)

    async def get_user_history(self, user_id):
        return await self.history_table.get(user_id)

    async def get_user_stats(self, user_id):
        return await self.stats_table.get(user_id)
