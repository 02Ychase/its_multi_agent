import pymysql
from config.settings import settings
from dbutils.pooled_db import PooledDB


class DatabasePool:
    _pool = None

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            cls._pool = PooledDB(
                creator=pymysql,
                maxconnections=5,
                host=settings.MYSQL_HOST,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                port=settings.MYSQL_PORT,
                database=settings.MYSQL_DATABASE,
                charset="utf8mb4",
                connect_timeout=10,
            )
        return cls._pool

    @classmethod
    def get_connection(cls):
        return cls.get_pool().connection()
