class MockCollection:
    def __init__(self):
        self._documents = []

    def insert_one(self, document):
        self._documents.append(document)
        return {"inserted_id": len(self._documents)}

    def find(self, query=None):
        if not query:
            return self._documents
        # Basic matching logic
        return [doc for doc in self._documents if all(item in doc.items() for item in query.items())]

    def delete_one(self, query):
        for i, doc in enumerate(self._documents):
            if all(item in doc.items() for item in query.items()):
                del self._documents[i]
                return {"deleted_count": 1}
        return {"deleted_count": 0}


class MockMongoDBClient:
    def __init__(self):
        self._collections = {}

    def get_collection(self, collection_name):
        if collection_name not in self._collections:
            self._collections[collection_name] = MockCollection()
        return self._collections[collection_name]

    def close(self):
        self._collections.clear()


# Singleton
_mock_mongo_client = MockMongoDBClient()

def get_mongo_client():
    return _mock_mongo_client
