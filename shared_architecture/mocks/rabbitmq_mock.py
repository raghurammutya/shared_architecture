class RabbitMQMockChannel:
    def __init__(self):
        self.published_messages = []

    def basic_publish(self, exchange, routing_key, body, properties=None):
        self.published_messages.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "body": body,
            "properties": properties
        })

def get_mock_rabbitmq_channel():
    return RabbitMQMockChannel()
