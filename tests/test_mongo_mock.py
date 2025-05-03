# tests/test_mongo_mock.py

from shared_architecture.utils import connection_manager

def test_mongo_find_one_positive():
    mongo = connection_manager.get_mongo()
    mongo.test_db.test_collection.find_one.return_value = {"user_id": 1}
    
    result = mongo.test_db.test_collection.find_one({"user_id": 1})
    assert result["user_id"] == 1

def test_mongo_find_one_not_found():
    mongo = connection_manager.get_mongo()
    mongo.test_db.test_collection.find_one.return_value = None
    
    result = mongo.test_db.test_collection.find_one({"user_id": 999})
    assert result is None