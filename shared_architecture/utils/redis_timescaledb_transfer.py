from typing import List, Dict
from redis import Redis
from sqlalchemy.orm import Session

def redis_to_timescaledb(
    redis_client: Redis,
    session: Session,
    model,
    keys: List[str],
    schema_class,
    batch_size: int = 500,
    log_progress: bool = False
):
    """
    Transfer data from Redis to TimescaleDB.
    """
    from shared_architecture.utils.data_adapter_timescaledb import process_bulk_insert, apply_defaults_and_conversions

    def fetch_and_prepare():
        pipeline = redis_client.pipeline()
        for key in keys:
            pipeline.get(key)
        values = pipeline.execute()

        # Prepare data for TimescaleDB using schema validation and conversion
        raw_data = [{"redis_key": k, "value": v} for k, v in zip(keys, values) if v is not None]
        return apply_defaults_and_conversions(schema_class, raw_data)

    enriched_data = fetch_and_prepare()

    process_bulk_insert(
        session=session,
        model=model,
        schema_class=schema_class,
        data=enriched_data,
        batch_size=batch_size,
        parallel=False,
        log_progress=log_progress
    )

def timescaledb_to_redis(
    session: Session,
    query,
    redis_client: Redis,
    key_field: str,
    value_field: str,
    batch_size: int = 500,
    log_progress: bool = False
):
    """
    Transfer data from TimescaleDB to Redis.
    """
    result = session.execute(query).fetchall()
    data_to_set = {row._mapping[key_field]: row._mapping[value_field] for row in result}

    from shared_architecture.utils.data_adapter_redis import bulk_set

    bulk_set(
        redis_client=redis_client,
        key_value_pairs=data_to_set,
        batch_size=batch_size,
        parallel=False,
        log_progress=log_progress
    )
