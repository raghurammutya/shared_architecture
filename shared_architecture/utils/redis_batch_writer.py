# shared_architecture/redis/redis_batch_writer.py
import asyncio
import json
import logging
from typing import Any, Dict

class RedisBatchWriter:
    def __init__(self, redis):
        self.redis = redis
        self.batch_queue = asyncio.Queue()
        self.failure_queue = asyncio.Queue()
        self.batch_size = 100
        self.flush_interval = 2  # seconds

    async def enqueue(self, stream: str, data: Dict[str, Any]) -> None:
        await self.batch_queue.put((stream, data))

    async def run_batch_processor(self):
        logging.info("RedisBatchWriter: Batch processor started.")
        while True:
            try:
                items = []
                try:
                    # Wait for first item
                    items.append(await asyncio.wait_for(self.batch_queue.get(), timeout=self.flush_interval))
                except asyncio.TimeoutError:
                    continue

                # Drain the queue for the rest of the batch
                while len(items) < self.batch_size:
                    try:
                        items.append(self.batch_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break

                # Group by stream
                streams: Dict[str, list] = {}
                for stream, data in items:
                    streams.setdefault(stream, []).append(data)

                # Write each stream
                for stream, records in streams.items():
                    try:
                        await self.redis.xadd(stream, {"data": json.dumps(records)}, maxlen=1000, approximate=True)
                        logging.info(f"RedisBatchWriter: ✅ Wrote {len(records)} records to {stream}")
                    except Exception as e:
                        logging.error(f"RedisBatchWriter: ❌ Failed to write to {stream}: {e}")
                        for record in records:
                            await self.failure_queue.put((stream, record))

            except Exception as e:
                logging.exception(f"RedisBatchWriter: Unexpected error: {e}")

    async def process_failure_queue(self):
        logging.info("RedisBatchWriter: Failure queue processor started.")
        while True:
            try:
                stream, record = await self.failure_queue.get()
                try:
                    await self.redis.xadd(stream, {"data": json.dumps([record])}, maxlen=1000, approximate=True)
                    logging.info(f"RedisBatchWriter: ✅ Retried and wrote to {stream}")
                except Exception as e:
                    logging.warning(f"RedisBatchWriter: ⚠️ Retry failed for {stream}: {e}")
                    await asyncio.sleep(5)  # back off before requeuing
                    await self.failure_queue.put((stream, record))
            except Exception as e:
                logging.exception(f"RedisBatchWriter: Error in failure queue: {e}")
