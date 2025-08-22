"""
Optimized Vector Store with Caching
Dramatically improves performance by caching embeddings
"""

import os
import json
import hashlib
import pickle
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import openai
from dotenv import load_dotenv

load_dotenv()

class CachedVectorStore:
    def __init__(self, cache_dir: str = ".vector_cache"):
        self.neon_conn_string = os.getenv('NEON_CONNECTION_STRING')
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = "text-embedding-ada-002"
        self.embedding_dimension = 1536
        
        # Setup cache
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.embedding_cache = self._load_cache()
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _load_cache(self) -> Dict:
        """Load embedding cache from disk"""
        cache_file = os.path.join(self.cache_dir, "embeddings.pkl")
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save embedding cache to disk"""
        cache_file = os.path.join(self.cache_dir, "embeddings.pkl")
        with open(cache_file, 'wb') as f:
            pickle.dump(self.embedding_cache, f)
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(f"{self.embedding_model}:{text}".encode()).hexdigest()
    
    def get_connection(self):
        """Create database connection"""
        return psycopg2.connect(self.neon_conn_string)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with caching"""
        cache_key = self._get_cache_key(text)
        
        # Check cache
        if cache_key in self.embedding_cache:
            self.cache_hits += 1
            return self.embedding_cache[cache_key]
        
        # Generate new embedding
        self.cache_misses += 1
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            
            # Cache it
            self.embedding_cache[cache_key] = embedding
            
            # Save cache periodically
            if self.cache_misses % 10 == 0:
                self._save_cache()
            
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def find_similar_queries_fast(self, question: str, limit: int = 3) -> List[Dict]:
        """Fast similarity search with pre-computed embeddings"""
        embedding = self.generate_embedding(question)
        if not embedding:
            return []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Use pre-computed embeddings
                cur.execute("""
                    SELECT 
                        question,
                        sql_query,
                        success_rate,
                        execution_count,
                        1 - (embedding <=> %s::vector) as similarity
                    FROM query_embeddings
                    WHERE success_rate > 0.5
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, embedding, limit))
                
                return cur.fetchall()
    
    def batch_store_queries(self, queries: List[Dict]):
        """Store multiple queries efficiently"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for query_data in queries:
                    embedding = self.generate_embedding(query_data['question'])
                    if embedding:
                        cur.execute("""
                            INSERT INTO query_embeddings 
                            (question, sql_query, embedding, avg_execution_time)
                            VALUES (%s, %s, %s::vector, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            query_data['question'],
                            query_data['sql'],
                            embedding,
                            query_data.get('execution_time', 0.05)
                        ))
                
                conn.commit()
        
        # Save cache after batch
        self._save_cache()
    
    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cache_size': len(self.embedding_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'memory_mb': len(str(self.embedding_cache)) / 1024 / 1024
        }
    
    def preload_common_queries(self):
        """Preload embeddings for common queries to warm cache"""
        common_patterns = [
            "Show all",
            "Count",
            "Get recent",
            "Find by id",
            "Show active",
            "List with status",
            "Group by",
            "Order by date",
            "Join tables",
            "Calculate total"
        ]
        
        print("🔥 Warming embedding cache...")
        for pattern in common_patterns:
            self.generate_embedding(pattern)
        
        self._save_cache()
        print(f"✅ Cache warmed with {len(common_patterns)} patterns")

# Quick migration function
def migrate_to_cached_store():
    """Migrate existing vector store to cached version"""
    from vector_store import VectorStore
    
    print("🔄 Migrating to cached vector store...")
    
    old_store = VectorStore()
    new_store = CachedVectorStore()
    
    # Get existing embeddings
    with old_store.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT question, sql_query 
                FROM query_embeddings 
                LIMIT 100
            """)
            existing = cur.fetchall()
    
    # Pre-generate embeddings for cache
    for row in existing:
        new_store.generate_embedding(row['question'])
    
    new_store._save_cache()
    
    stats = new_store.get_cache_stats()
    print(f"✅ Migration complete!")
    print(f"   Cache size: {stats['cache_size']} embeddings")
    print(f"   Hit rate: {stats['hit_rate']}")
    
    return new_store

if __name__ == "__main__":
    # Test the cached store
    store = CachedVectorStore()
    store.preload_common_queries()
    
    # Test performance
    import time
    
    test_query = "Show all customers"
    
    # First call (cache miss)
    start = time.time()
    result1 = store.find_similar_queries_fast(test_query)
    time1 = time.time() - start
    
    # Second call (cache hit)
    start = time.time()
    result2 = store.find_similar_queries_fast(test_query)
    time2 = time.time() - start
    
    print(f"\n⚡ Performance Test:")
    print(f"  First call (cache miss): {time1:.3f}s")
    print(f"  Second call (cache hit): {time2:.3f}s")
    print(f"  Speedup: {time1/time2:.1f}x faster")
    
    print(f"\n📊 Cache Stats:")
    for key, value in store.get_cache_stats().items():
        print(f"  {key}: {value}")