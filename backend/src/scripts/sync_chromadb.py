#!/usr/bin/env python3
"""
Sync ChromaDB with SQLite database.
Removes vectors that no longer have corresponding dataset records.
"""

import sys
import os
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    # Get valid dataset IDs from SQLite
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'datasets.db')
    
    print(f"Reading from: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM datasets")
    valid_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    
    print(f"Valid dataset IDs in SQLite: {len(valid_ids)}")
    
    # Connect to ChromaDB
    try:
        import chromadb
        
        chroma_path = os.path.join(os.path.dirname(__file__), '..', '..', 'chroma_db')
        client = chromadb.PersistentClient(path=chroma_path)
        collection = client.get_or_create_collection(name="dataset_embeddings")
        
        # Get all IDs in ChromaDB
        result = collection.get()
        chroma_ids = set(result['ids']) if result['ids'] else set()
        
        print(f"Vector IDs in ChromaDB: {len(chroma_ids)}")
        
        # Find orphaned vectors
        orphaned_ids = chroma_ids - valid_ids
        
        if orphaned_ids:
            print(f"\nDeleting {len(orphaned_ids)} orphaned vectors...")
            collection.delete(ids=list(orphaned_ids))
            print("Done!")
        else:
            print("\nNo orphaned vectors found.")
        
        # Verify final count
        final_count = collection.count()
        print(f"\nFinal ChromaDB count: {final_count}")
        
    except ImportError:
        print("ChromaDB not installed. Skipping vector sync.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
