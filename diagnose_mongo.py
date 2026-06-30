from pymongo import MongoClient

MONGO_URI = 'mongodb://localhost:27017/'
DB_NAME = 'klause'

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

for collection_name in db.list_collection_names():
    print(f'Checking collection: {collection_name}')
    col = db[collection_name]
    # Try to find one of the suspected IDs
    sample_id = '6a411b0567d519482254669f'
    doc = col.find_one({'_id': sample_id})
    if doc:
        print(f'Found document in {collection_name}!')
    else:
        # Try checking if ID is stored in a different field
        doc = col.find_one({'id': sample_id})
        if doc:
            print(f'Found document (under id field) in {collection_name}!')
        else:
            print('Document not found in this collection.')