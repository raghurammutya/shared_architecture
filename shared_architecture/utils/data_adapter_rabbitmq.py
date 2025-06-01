# shared_architecture/data_adapters/data_adapter_rabbitmq.py

from aio_pika import Message
from typing import Dict, Any
import json
from shared_architecture.utils.logging_utils import log_error


async def rabbitmq_publish_message(channel, queue_name: str, payload: Dict[str, Any]):
    try:
        message = Message(body=json.dumps(payload).encode())
        await channel.default_exchange.publish(message, routing_key=queue_name)
    except Exception as e:
        log_error(f"[RabbitMQ] Failed to publish message to {queue_name}: {e}")
        raise


async def rabbitmq_consume_messages(queue, callback):
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                    await callback(payload)
                except Exception as e:
                    log_error(f"[RabbitMQ] Error processing message: {e}")
