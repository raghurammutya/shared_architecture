from typing import List, Dict
from redis import Redis
from pymongo.collection import Collection

def redis_to_mongodb(
    redis_client: Redis,
    mongo_collection: Collection,
    keys: List[str],
    batch_size: int = 500,
    log_progress: bool = False
):
    """
    Transfer data from Redis to MongoDB.
    """
    from shared_architecture.utils.data_adapter_mongodb import mongodb_bulk_insert

    def fetch_and_prepare():
        pipeline = redis_client.pipeline()
        for key in keys:
            pipeline.get(key)
        values = pipeline.execute()

        # Prepare documents for MongoDB
        documents = [{"redis_key": k, "value": v} for k, v in zip(keys, values) if v is not None]
        return documents

    documents_to_insert = fetch_and_prepare()
    mongodb_bulk_insert(mongo_collection, documents_to_insert, batch_size=batch_size, log_progress=log_progress)

def mongodb_to_redis(
    mongo_collection: Collection,
    redis_client: Redis,
    key_field: str,
    value_field: str,
    filter_query: Dict = {},
    batch_size: int = 500,
    log_progress: bool = False
):
    """
    Transfer data from MongoDB to Redis.
    """
    cursor = mongo_collection.find(filter_query)
    data_to_set = {doc[key_field]: doc[value_field] for doc in cursor}

    from shared_architecture.utils.data_adapter_redis import redis_bulk_set

    redis_bulk_set(
        redis_client=redis_client,
        key_value_pairs=data_to_set,
        batch_size=batch_size,
        parallel=False,
        log_progress=log_progress
    )
