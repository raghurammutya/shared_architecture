class MockRabbitMQClient:
    def __init__(self):
        self.queues = {}

    def declare_queue(self, queue_name):
        if queue_name not in self.queues:
            self.queues[queue_name] = []

    def publish(self, queue_name, body):
        if queue_name not in self.queues:
            self.declare_queue(queue_name)
        self.queues[queue_name].append(body)

    def consume(self, queue_name):
        """
        Simulate consuming messages one by one.
        Returns None when the queue is empty.
        """
        if queue_name not in self.queues or not self.queues[queue_name]:
            return None
        return self.queues[queue_name].pop(0)

    def close(self):
        self.queues.clear()


# Singleton
_mock_rabbitmq_client = MockRabbitMQClient()

def get_rabbitmq_client():
    return _mock_rabbitmq_client
