"""
Batch Import Patterns into Vector Database
Efficiently stores all generated patterns with cached embeddings
"""

import os
import json
import time
from typing import List, Dict
from vector_store_cached import CachedVectorStore
from dotenv import load_dotenv

load_dotenv()

def batch_import_patterns(json_file: str):
    """Import patterns from JSON file into vector database"""
    print(f"📥 Importing patterns from: {json_file}")
    
    # Load patterns
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    patterns = data['patterns']
    print(f"Found {len(patterns)} patterns to import")
    
    # Initialize cached vector store
    store = CachedVectorStore()
    
    # Pre-warm cache with common terms
    print("\n🔥 Pre-warming cache...")
    common_terms = ['show', 'get', 'find', 'count', 'calculate', 'group', 'order', 'recent', 'status', 'total']
    for term in common_terms:
        store.generate_embedding(term)
    
    # Batch process patterns
    print("\n📊 Processing patterns in batches...")
    batch_size = 10
    total_stored = 0
    total_skipped = 0
    start_time = time.time()
    
    for i in range(0, len(patterns), batch_size):
        batch = patterns[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(patterns) + batch_size - 1) // batch_size
        
        print(f"\n  Batch {batch_num}/{total_batches}:")
        
        # Prepare batch for storage
        queries_to_store = []
        for pattern in batch:
            queries_to_store.append({
                'question': pattern['question'],
                'sql': pattern['sql'],
                'execution_time': 0.05,
                'metadata': {
                    'type': pattern.get('type', 'unknown'),
                    'source': 'batch_import',
                    'batch': json_file
                }
            })
        
        # Store batch
        try:
            store.batch_store_queries(queries_to_store)
            total_stored += len(queries_to_store)
            print(f"    ✅ Stored {len(queries_to_store)} patterns")
        except Exception as e:
            print(f"    ❌ Error: {e}")
            total_skipped += len(queries_to_store)
        
        # Show progress
        progress = ((i + len(batch)) / len(patterns)) * 100
        elapsed = time.time() - start_time
        rate = total_stored / elapsed if elapsed > 0 else 0
        print(f"    Progress: {progress:.1f}% | Rate: {rate:.1f} patterns/sec")
        
        # Show cache stats periodically
        if batch_num % 5 == 0:
            cache_stats = store.get_cache_stats()
            print(f"    Cache: {cache_stats['hit_rate']} hit rate, {cache_stats['cache_size']} embeddings")
    
    # Final statistics
    total_time = time.time() - start_time
    final_cache_stats = store.get_cache_stats()
    
    print("\n" + "=" * 50)
    print("✅ Import Complete!")
    print(f"  • Patterns imported: {total_stored}")
    print(f"  • Patterns skipped: {total_skipped}")
    print(f"  • Time taken: {total_time:.2f} seconds")
    print(f"  • Average rate: {total_stored/total_time:.1f} patterns/sec")
    print(f"\n📊 Cache Statistics:")
    print(f"  • Cache size: {final_cache_stats['cache_size']} embeddings")
    print(f"  • Hit rate: {final_cache_stats['hit_rate']}")
    print(f"  • Cache hits: {final_cache_stats['cache_hits']}")
    print(f"  • Cache misses: {final_cache_stats['cache_misses']}")
    
    # Check current database status
    with store.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM query_embeddings")
            total_in_db = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(DISTINCT question) FROM query_embeddings")
            unique_patterns = cur.fetchone()[0]
    
    print(f"\n🗄️ Database Status:")
    print(f"  • Total patterns: {total_in_db}")
    print(f"  • Unique patterns: {unique_patterns}")
    
    return total_stored

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        # Use the most recent patterns file
        import glob
        pattern_files = glob.glob("patterns_batch_*.json")
        if pattern_files:
            json_file = sorted(pattern_files)[-1]
        else:
            print("❌ No pattern files found!")
            sys.exit(1)
    
    batch_import_patterns(json_file)