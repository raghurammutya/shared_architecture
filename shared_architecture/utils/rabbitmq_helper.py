import pika
import json
import logging

def publish_message(rabbitmq_url, queue_name, message):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)

        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
        )
        logging.info(f"Message published to {queue_name}")
        connection.close()
    except Exception as e:
        logging.error(f"Error publishing message to {queue_name}: {e}")
        raise
