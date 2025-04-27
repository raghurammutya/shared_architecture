from pymongo import MongoClient

uri = "mongodb://tradmin:tradpass@localhost:27017/tradingdb"  # Your exact URI

try:
    client = MongoClient(uri)
    client.admin.command('ping')  # Try a simple command
    print("Connection successful!")
except Exception as e:
    print(f"Connection failed: {e}")
finally:
    if client:
        client.close()