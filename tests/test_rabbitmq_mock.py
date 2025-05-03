# tests/test_rabbitmq_mock.py

from shared_architecture.utils import connection_manager

def test_publish_message_to_queue():
    rabbit = connection_manager.get_rabbitmq_channel()
    rabbit.basic_publish(exchange='', routing_key='orders_queue', body='{"order_id": 123}')
    
    assert rabbit.published_messages[-1]["queue"] == "orders_queue"
    assert rabbit.published_messages[-1]["body"] == '{"order_id": 123}'