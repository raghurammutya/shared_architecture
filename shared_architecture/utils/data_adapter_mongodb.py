from typing import List, Dict
from pymongo.collection import Collection
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Counter
import time
import pymongo
# Prometheus Metrics
MONGO_BATCH_SUCCESS_COUNT = Counter('mongodb_bulk_operation_success_total', 'Total successful MongoDB bulk operations')
MONGO_BATCH_FAILURE_COUNT = Counter('mongodb_bulk_operation_failure_total', 'Total failed MongoDB bulk operations')

def mongodb_retry_with_backoff(fn, retries=3, delay=1):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay * (2 ** attempt))
            else:
                raise e

def mongodb_bulk_insert(collection: Collection, documents: List[Dict], parallel: bool = False, batch_size: int = 500, retry_attempts: int = 3, log_progress: bool = False):
    batches = [documents[i:i + batch_size] for i in range(0, len(documents), batch_size)]

    def commit_batch(batch):
        def _commit():
            collection.insert_many(batch)
            if log_progress:
                print(f"Inserted MongoDB batch of {len(batch)} documents.")
            MONGO_BATCH_SUCCESS_COUNT.inc()
        mongodb_retry_with_backoff(_commit, retries=retry_attempts)

    if parallel:
        with ThreadPoolExecutor() as executor:
            list(executor.map(commit_batch, batches))
    else:
        for batch in batches:
            try:
                commit_batch(batch)
            except Exception as e:
                MONGO_BATCH_FAILURE_COUNT.inc()
                print(f"MongoDB batch insert failed: {e}")

def mongodb_bulk_update(collection: Collection, updates: List[Dict], retry_attempts: int = 3, log_progress: bool = False):
    """
    Each update dict should contain:
    - 'filter': filter query
    - 'update': update query
    """
    def _commit():
        operations = [pymongo.UpdateOne(u['filter'], u['update']) for u in updates]
        if operations:
            collection.bulk_write(operations)
            if log_progress:
                print(f"Executed MongoDB bulk update of {len(operations)} operations.")
            MONGO_BATCH_SUCCESS_COUNT.inc()
    mongodb_retry_with_backoff(_commit, retries=retry_attempts)

def mongodb_shard_key_validation(documents: List[Dict], shard_key: str):
    """
    Validate that all documents include the shard key.
    """
    for doc in documents:
        if shard_key not in doc:
            raise ValueError(f"Missing shard key: {shard_key} in document {doc}")
    return True
