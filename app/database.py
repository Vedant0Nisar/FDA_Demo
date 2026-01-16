import os
import logging
from contextlib import asynccontextmanager
from typing import Generator
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database Configuration
DEFAULT_DB_URL = "postgresql://postgres:1234@localhost:5432/fda_track"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

class Database:
    _pool = None

    @classmethod
    def initialize(cls):
        if cls._pool is None:
            try:
                cls._pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    dsn=DATABASE_URL
                )
                logger.info("Database connection pool created successfully.")
            except Exception as e:
                logger.error(f"Failed to create database connection pool: {e}")
                raise e

    @classmethod
    def get_connection(cls):
        if cls._pool is None:
            cls.initialize()
        return cls._pool.getconn()

    @classmethod
    def return_connection(cls, conn):
        if cls._pool:
            cls._pool.putconn(conn)

    @classmethod
    def close_all(cls):
        if cls._pool:
            cls._pool.closeall()
            logger.info("Database connection pool closed.")

# Dependency for FastAPI
def get_db() -> Generator:
    """
    Yields a database cursor (RealDictCursor) for a single request.
    Handles commit/rollback automatically.
    """
    conn = None
    try:
        conn = Database.get_connection()
        # Use RealDictCursor to access columns by name
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except psycopg2.DatabaseError as e:
        if conn:
            conn.rollback()
        logger.error(f"Database Transaction Error: {e}")
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected Database Error: {e}")
        raise e
    finally:
        if conn:
            Database.return_connection(conn)

# Application Lifecycle Hook
@asynccontextmanager
async def lifespan_db(app: FastAPI):
    Database.initialize()
    yield
    Database.close_all()
