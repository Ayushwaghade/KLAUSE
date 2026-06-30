from pymongo import MongoClient

# Connection URI
MONGO_URI = 'mongodb://localhost:27017/'

def remove_duplicates():
    try:
        client = MongoClient(MONGO_URI)
        db = client['klause']  # Updated to 'klause'
        collection = db['notes']
        
        # List of duplicate IDs identified in memory
        duplicate_ids = [
            '6a411b0567d519482254669f', 
            '6a411b952971c142e8989411', 
            '6a415b675410f8250e247548', 
            '6a4164e7c97057a1dc2a76bd'
        ]
        
        result = collection.delete_many({'_id': {'$in': duplicate_ids}})
        print(f'Successfully deleted {result.deleted_count} duplicate documents.')
    except Exception as e:
        print(f'An error occurred: {e}')

if __name__ == '__main__':
    remove_duplicates()