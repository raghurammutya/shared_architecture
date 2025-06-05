from typing import List, Dict, Type
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Counter
import asyncio
import time
import pytz
from datetime import datetime

from shared_architecture.config.global_settings import DEFAULT_TIMEZONE, DEFAULT_CURRENCY
from .safe_converters import safe_convert,safe_convert_bool, safe_convert_int, safe_convert_float, safe_parse_datetime

# Prometheus Metrics
BATCH_SUCCESS_COUNT = Counter('timescaledb_bulk_insert_success_total', 'Total successful TimescaleDB bulk inserts')
BATCH_FAILURE_COUNT = Counter('timescaledb_bulk_insert_failure_total', 'Total failed TimescaleDB bulk inserts')


def convert_to_timezone(value, timezone_str=DEFAULT_TIMEZONE):
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        target_tz = pytz.timezone(timezone_str)
        return value.astimezone(target_tz)
    except Exception:
        return value


def apply_defaults_and_conversions(schema_class: Type[BaseModel], data: List[Dict]) -> List[Dict]:
    enriched_data = []
    for record in data:
        processed_record = {}
        for field_name, field_info in schema_class.model_fields.items():
            raw_value = record.get(field_name, field_info.default)

            if field_info.annotation == bool:
                processed_record[field_name] = safe_convert_bool(raw_value)
            elif field_info.annotation == int:
                processed_record[field_name] = safe_convert_int(raw_value)
            elif field_info.annotation == float:
                processed_record[field_name] = safe_convert_float(raw_value)
            else:
                processed_record[field_name] = raw_value

            if "timestamp" in field_name.lower() or "datetime" in field_name.lower() or "time" in field_info.description.lower():
                processed_record[field_name] = convert_to_timezone(processed_record[field_name])

            if "currency" in field_name.lower():
                if not processed_record[field_name]:
                    processed_record[field_name] = DEFAULT_CURRENCY

        try:
            validated = schema_class(**processed_record).dict()
        except ValidationError as e:
            raise ValueError(f"Validation error: {e}")

        enriched_data.append(validated)

    return enriched_data


def timescaledb_retry_with_backoff(fn, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (2 ** attempt))
            else:
                raise e


def timescaledb_process_bulk_insert(session: Session, model, schema_class: Type[BaseModel], data: List[Dict], batch_size: int = 500, parallel: bool = False, retry_attempts: int = 3, log_progress: bool = False):
    enriched_data = apply_defaults_and_conversions(schema_class, data)
    batches = [enriched_data[i:i + batch_size] for i in range(0, len(enriched_data), batch_size)]

    def commit_batch(batch):
        def _commit():
            session.bulk_insert_mappings(model, batch)
            session.commit()
            if log_progress:
                print(f"Committed batch of {len(batch)} records.")
            BATCH_SUCCESS_COUNT.inc()
        timescaledb_retry_with_backoff(_commit, retries=retry_attempts)

    if parallel:
        with ThreadPoolExecutor() as executor:
            list(executor.map(commit_batch, batches))
    else:
        for batch in batches:
            try:
                commit_batch(batch)
            except Exception as e:
                BATCH_FAILURE_COUNT.inc()
                print(f"Batch failed: {e}")


async def timescaledb_async_process_bulk_insert(session: Session, model, schema_class: Type[BaseModel], data: List[Dict], batch_size: int = 500, retry_attempts: int = 3, log_progress: bool = False):
    enriched_data = apply_defaults_and_conversions(schema_class, data)
    batches = [enriched_data[i:i + batch_size] for i in range(0, len(enriched_data), batch_size)]

    async def commit_batch(batch):
        def _commit():
            session.bulk_insert_mappings(model, batch)
            session.commit()
            if log_progress:
                print(f"Committed batch of {len(batch)} records.")
            BATCH_SUCCESS_COUNT.inc()
        timescaledb_retry_with_backoff(_commit, retries=retry_attempts)

    for batch in batches:
        await commit_batch(batch)


def timescaledb_process_bulk_query(session: Session, query, timezone: str = DEFAULT_TIMEZONE) -> List[Dict]:
    result = session.execute(query).fetchall()
    output = []
    for row in result:
        record = dict(row._mapping)
        if 'timestamp' in record:
            record['timestamp'] = convert_to_timezone(record['timestamp'], timezone)
        output.append(record)
    return output


# Placeholder for future chunk placement awareness
def timescaledb_place_data_in_chunk(batch):
    return batch
