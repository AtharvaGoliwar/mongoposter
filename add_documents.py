from pymongo import MongoClient
import time

# Replace this with your own URI if using MongoDB Atlas
MONGO_URI = "abc"
DATABASE_NAME = "db"
COLLECTION_NAME = "collection"

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Access database and collection correctly
db = client[DATABASE_NAME]
collection = db[COLLECTION_NAME]

# Sample document(s) to insert
documents = [
    {"name": "Alice", "age": 25, "email": "alice@example.com"},
    {"name": "Bob", "age": 30, "email": "bob@example.com"}
]

sample_code = """def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

# Test the function
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")"""

new_code = """class Main{
    public static void main(String[] args){
        System.out.println("Hello World");
    }
}"""
    
document = {
        "title": "Print stuff",
        "language": "python",
        "code": new_code,
        "timestamp": time.time(),
        "type":"code",
    }

# Insert the documents
insert_result = collection.insert_one(document)

# Show inserted IDs
# print("Inserted IDs:", insert_result.inserted_ids)

