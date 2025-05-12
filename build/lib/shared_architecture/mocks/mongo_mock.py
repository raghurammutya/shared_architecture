class MongoMock:
    def __init__(self):
        self.databases = {}

    def __getattr__(self, db_name):
        return self.databases.setdefault(db_name, MongoDatabase())

class MongoDatabase:
    def __init__(self):
        self.collections = {}

    def __getattr__(self, collection_name):
        return self.collections.setdefault(collection_name, MongoCollection())

class MongoCollection:
    def __init__(self):
        self.documents = []

    def insert_one(self, document):
        self.documents.append(document)
        return {"inserted_id": len(self.documents)}

    def find_one(self, filter_dict):
        for doc in self.documents:
            if all(doc.get(k) == v for k, v in filter_dict.items()):
                return doc
        return None
