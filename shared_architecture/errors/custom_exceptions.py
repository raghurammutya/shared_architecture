class ServiceUnavailableError(Exception):
    """
    Exception raised when a required service is unavailable.

    Attributes:
        service_name (str, optional): The name of the unavailable service.
        message (str): Explanation of why the service is unavailable.
    """
    def __init__(self, service_name: str = None, message: str = "Service unavailable"):
        self.service_name = service_name
        if service_name:
            message = f"Service '{service_name}' unavailable"
        self.message = message
        super().__init__(self.message)
