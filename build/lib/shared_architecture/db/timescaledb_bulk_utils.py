# Standard Library Imports
import os
import time
import math
import logging
from asyncio import wait_for, TimeoutError

# Third-Party Library Imports
import pandas as pd
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import DeclarativeMeta
from sqlalchemy.dialects.postgresql import insert

# Typing-related Imports
from typing import List, Dict, Any, Callable, Type, Optional

def chunked(data, batch_size):
    """Yield successive chunks from data."""
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


async def bulk_upsert_async(
    model: Type[DeclarativeMeta],
    data_list: List[Dict[str, Any]],
    key_fields: List[str],
    session_factory: Callable[[], async_sessionmaker],
    timestamp_fields: Optional[Dict[str, List[str]]] = None,
    batch_size: int = 100,
) -> None:
    """
    Performs a batched upsert (insert + on conflict update) for a given SQLAlchemy model.

    Args:
        model: The SQLAlchemy model to upsert into.
        data_list: List of dictionaries with data to insert.
        key_fields: Fields used to identify conflicts (e.g., primary keys or unique constraints).
        session_factory: Callable that returns a new async session factory.
        timestamp_fields: Optional dict to auto-fill timestamp fields.
        batch_size: Size of each batch for insertion.
    """
    if not data_list:
        print("⚠️ No data to upsert.")
        return

    total_records = len(data_list)
    print(f"🔄 Starting bulk upsert: {total_records} records, batch size = {batch_size}")
    start_time = time.time()

    # Get valid model fields
    valid_columns = set(model.__table__.columns.keys())
    async_session_maker = session_factory()
    total_batches = math.ceil(len(data_list) / batch_size) 
    for batch_num, chunk in enumerate(chunked(data_list, batch_size), start=1):
        print(f"⏳ Preparing batch {batch_num} with {len(chunk)} records...")

        filtered_chunk = [
            {k: v for k, v in row.items() if k in valid_columns}
            for row in chunk
        ]
        if not filtered_chunk:
            print(f"⚠️ Batch {batch_num} is empty after filtering. Skipping.")
            continue

        print(f"🔍 First row of batch {batch_num}/{total_batches}")

        stmt = insert(model).values(filtered_chunk)

        update_fields = {
            col: getattr(stmt.excluded, col)
            for col in filtered_chunk[0].keys()
            if col not in key_fields
        }

        stmt = stmt.on_conflict_do_update(
            index_elements=key_fields,
            set_=update_fields
        )

        batch_start = time.time()
        async with async_session_maker() as session:
            try:
                await session.execute(text("SET LOCAL lock_timeout = '3s'"))
                print(f"🚀 Executing batch {batch_num}...")
                try:
                    await wait_for(session.execute(stmt), timeout=10)
                except TimeoutError:
                    print(f"❌ Timeout: Batch {batch_num} took too long to execute.")
                    await session.rollback()
                    continue
                await session.flush()  # Optional, before commit
                await session.commit()
                print(f"📦 Batch {batch_num} committed.")
                batch_time = time.time() - batch_start
                print(f"✅ Batch {batch_num} done in {batch_time:.2f}s")
            except Exception as e:
                print(f"❌ Error in batch {batch_num}: {e}")
                await session.rollback()

    total_time = time.time() - start_time
    print(f"🎉 Upsert complete: {total_records} records in {total_time:.2f}s")


async def upsert_dataframe(pool, table_name: str, dataframe: pd.DataFrame):
    """
    Bulk upsert a pandas DataFrame into a TimescaleDB table.
    """
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for _, row in dataframe.iterrows():
                    columns = ', '.join(row.index)
                    values_placeholders = ', '.join(f"${i+1}" for i in range(len(row)))
                    values = tuple(row.values)
                    query = f"INSERT INTO {table_name} ({columns}) VALUES ({values_placeholders})"
                    await conn.execute(query, *values)
        logging.info(f"✅ Bulk upserted {len(dataframe)} records into {table_name}.")
    except Exception as e:
        logging.exception(f"❌ Failed to upsert dataframe into {table_name}: {e}")
        raise e

async def get_asyncpg_pool():
    """
    Creates a connection pool for TimescaleDB using asyncpg.
    """
    try:
        pool = await asyncpg.create_pool(
            user=os.getenv("POSTGRES_USER", "tradmin"),
            password=os.getenv("POSTGRES_PASSWORD", "tradpass"),
            database=os.getenv("POSTGRES_DB", "tradingdb"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            min_size=1,
            max_size=10,
        )
        logging.info("✅ TimescaleDB connection pool created.")
        return pool
    except Exception as e:
        logging.exception("❌ Failed to create TimescaleDB connection pool.")
        raise e