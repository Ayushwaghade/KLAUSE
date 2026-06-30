import sqlite3

def inspect():
    try:
        conn = sqlite3.connect('./data/chroma/chroma.sqlite3')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'Tables found: {tables}')
        for table in tables:
            print(f'\nSchema for {table[0]}:')
            cursor.execute(f"PRAGMA table_info({table[0]});")
            print(cursor.fetchall())
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    inspect()