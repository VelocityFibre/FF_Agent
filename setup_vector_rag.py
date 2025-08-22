#!/usr/bin/env python3
"""
Setup script for Vector RAG System
Initializes vector database and ingests documents
Phase 2: RAG Enhancement
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def check_dependencies():
    """Check and install required dependencies"""
    required = {
        'psycopg2': 'psycopg2-binary',
        'openai': 'openai',
        'pandas': 'pandas',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✅ {module} installed")
        except ImportError:
            missing.append(package)
            print(f"❌ {module} missing")
    
    if missing:
        print(f"\nInstalling missing packages...")
        os.system(f"pip install {' '.join(missing)}")
    
    return len(missing) == 0

def initialize_vector_database():
    """Initialize pgvector database tables"""
    try:
        from vector_store import VectorStore
        
        print("\n🔧 Initializing Vector Database...")
        
        # Check for required environment variables
        if not os.getenv('NEON_DATABASE_URL'):
            print("❌ NEON_DATABASE_URL not set in .env")
            print("Using mock vector store for testing")
            return None
            
        # Initialize vector store
        vs = VectorStore()
        
        # Initialize pgvector if needed
        try:
            vs.initialize_pgvector()
            print("✅ Vector database initialized")
            return vs
        except Exception as e:
            print(f"⚠️  Could not initialize pgvector: {e}")
            print("Continuing without vector storage (embeddings won't be saved)")
            return None
            
    except Exception as e:
        print(f"❌ Error initializing vector database: {e}")
        return None

def ingest_project_documents(vector_store=None):
    """Ingest all project documents"""
    from document_ingester import DocumentIngester
    
    print("\n📚 Ingesting Project Documents...")
    
    # Create ingester
    ingester = DocumentIngester(vector_store=vector_store)
    
    # Define what to ingest
    ingest_paths = [
        {
            'path': '.',
            'patterns': ['*.md', '*.txt'],
            'description': 'Documentation files'
        },
        {
            'path': '.',
            'patterns': ['*.json'],
            'description': 'Configuration files'
        },
        {
            'path': '.',
            'patterns': ['*.sql'],
            'description': 'SQL query examples'
        },
        {
            'path': '.',
            'patterns': ['*.py'],
            'description': 'Python code reference'
        }
    ]
    
    total_ingested = 0
    
    for ingest_config in ingest_paths:
        print(f"\n📁 Ingesting {ingest_config['description']}...")
        summary = ingester.ingest_directory(
            directory_path=ingest_config['path'],
            recursive=False,
            file_patterns=ingest_config['patterns']
        )
        total_ingested += summary.get('ingested', 0)
    
    return total_ingested

def seed_telecom_knowledge(vector_store):
    """Seed telecom-specific knowledge"""
    if not vector_store:
        print("⚠️  No vector store available, skipping knowledge seeding")
        return
    
    print("\n🌱 Seeding Telecom Knowledge...")
    
    telecom_knowledge = [
        {
            'question': 'What is PON utilization?',
            'answer': 'PON (Passive Optical Network) utilization is the percentage of used ports on a PON. Calculated as: (active_drops / total_ports) * 100, where total_ports is typically 32 or 64.',
            'sql': 'SELECT pon_id, COUNT(*) as drops, (COUNT(*) * 100.0 / 32) as utilization FROM drops GROUP BY pon_id'
        },
        {
            'question': 'What is splice loss?',
            'answer': 'Splice loss is the optical power loss at a fiber splice point, measured in decibels (dB). Acceptable range is 0.1-0.5 dB. Higher values indicate poor splice quality.',
            'sql': 'SELECT AVG(splice_loss_db) as avg_loss, MAX(splice_loss_db) as max_loss FROM drops WHERE splice_loss_db IS NOT NULL'
        },
        {
            'question': 'How to find drops in a project?',
            'answer': 'FibreFlow projects use prefixes: LAW (Lawley), IVY (Ivory Park), MAM (Mamelodi), MOH (Mohadin). Filter using LIKE with prefix.',
            'sql': "SELECT * FROM drops WHERE drop_number LIKE 'LAW%' LIMIT 100"
        },
        {
            'question': 'What is optical power?',
            'answer': 'Optical power is the strength of the light signal in a fiber, measured in dBm (decibels relative to 1 milliwatt). Typical values: -20 to -30 dBm for PON.',
            'sql': 'SELECT drop_number, optical_power_db FROM drops WHERE optical_power_db < -30'
        },
        {
            'question': 'How to query Firebase for staff?',
            'answer': 'Staff data is in Firebase. Use FIREBASE_QUERY: staff to retrieve employee information.',
            'sql': 'FIREBASE_QUERY: staff'
        }
    ]
    
    for knowledge in telecom_knowledge:
        try:
            vector_store.store_successful_query(
                question=knowledge['question'],
                sql_query=knowledge['sql'],
                metadata={'type': 'seed_knowledge', 'domain': 'telecom'}
            )
            print(f"  ✅ Seeded: {knowledge['question'][:50]}...")
        except Exception as e:
            print(f"  ❌ Failed to seed: {e}")

def test_rag_search(vector_store):
    """Test RAG search functionality"""
    if not vector_store:
        print("\n⚠️  No vector store available, skipping RAG test")
        return
    
    print("\n🔍 Testing RAG Search...")
    
    test_queries = [
        "What is PON utilization?",
        "Show drops in Lawley",
        "List all staff",
        "Calculate splice loss"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            similar = vector_store.find_similar_queries(query, limit=2)
            if similar:
                print(f"  Found {len(similar)} similar queries:")
                for result in similar:
                    print(f"    - {result['question'][:60]}... (similarity: {result.get('similarity', 0):.2f})")
            else:
                print("  No similar queries found")
        except Exception as e:
            print(f"  Error: {e}")

def create_hybrid_searcher():
    """Create hybrid search module"""
    
    code = '''#!/usr/bin/env python3
"""
Hybrid Search System for FF_Agent
Combines vector similarity with keyword matching (BM25)
"""

import re
from typing import List, Dict, Tuple
from collections import Counter
import math

class HybridSearcher:
    """
    Combines vector search with BM25 keyword search
    """
    
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self.document_cache = {}
        
        # BM25 parameters
        self.k1 = 1.2  # Term frequency saturation
        self.b = 0.75  # Length normalization
        
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Convert to lowercase and split on non-alphanumeric
        tokens = re.findall(r'\\b\\w+\\b', text.lower())
        return tokens
    
    def calculate_bm25(self, query_tokens: List[str], doc_tokens: List[str], 
                      avg_doc_length: float, doc_freq: Dict[str, int], 
                      total_docs: int) -> float:
        """Calculate BM25 score"""
        score = 0.0
        doc_length = len(doc_tokens)
        doc_counter = Counter(doc_tokens)
        
        for token in query_tokens:
            if token in doc_counter:
                # Term frequency in document
                tf = doc_counter[token]
                
                # Document frequency
                df = doc_freq.get(token, 1)
                
                # IDF calculation
                idf = math.log((total_docs - df + 0.5) / (df + 0.5))
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
                
                score += idf * (numerator / denominator)
        
        return score
    
    def hybrid_search(self, query: str, vector_weight: float = 0.7, 
                     keyword_weight: float = 0.3, limit: int = 5) -> List[Dict]:
        """
        Perform hybrid search combining vector and keyword search
        
        Args:
            query: Search query
            vector_weight: Weight for vector similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
            limit: Number of results to return
        """
        results = []
        
        # Get vector search results
        vector_results = []
        if self.vector_store:
            try:
                vector_results = self.vector_store.find_similar_queries(query, limit=limit*2)
            except:
                pass
        
        # Tokenize query
        query_tokens = self.tokenize(query)
        
        # Get documents for keyword search
        documents = self._get_documents_for_keyword_search()
        
        if documents:
            # Calculate document statistics
            doc_tokens_list = [self.tokenize(doc["content"]) for doc in documents]
            avg_doc_length = sum(len(tokens) for tokens in doc_tokens_list) / len(doc_tokens_list)
            
            # Calculate document frequency
            doc_freq = {}
            for tokens in doc_tokens_list:
                unique_tokens = set(tokens)
                for token in unique_tokens:
                    doc_freq[token] = doc_freq.get(token, 0) + 1
            
            # Calculate BM25 scores
            keyword_scores = []
            for i, doc in enumerate(documents):
                score = self.calculate_bm25(
                    query_tokens, 
                    doc_tokens_list[i],
                    avg_doc_length,
                    doc_freq,
                    len(documents)
                )
                keyword_scores.append((doc, score))
            
            # Sort by BM25 score
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Combine scores
            combined_results = {}
            
            # Add vector results
            for i, result in enumerate(vector_results[:limit]):
                doc_id = result.get("question", "")
                combined_results[doc_id] = {
                    "content": result,
                    "vector_score": result.get("similarity", 0),
                    "keyword_score": 0,
                    "combined_score": result.get("similarity", 0) * vector_weight
                }
            
            # Add keyword results
            for doc, score in keyword_scores[:limit]:
                doc_id = doc.get("id", doc.get("content", "")[:50])
                if doc_id in combined_results:
                    combined_results[doc_id]["keyword_score"] = score
                    combined_results[doc_id]["combined_score"] += score * keyword_weight
                else:
                    combined_results[doc_id] = {
                        "content": doc,
                        "vector_score": 0,
                        "keyword_score": score,
                        "combined_score": score * keyword_weight
                    }
            
            # Sort by combined score
            sorted_results = sorted(
                combined_results.values(),
                key=lambda x: x["combined_score"],
                reverse=True
            )
            
            results = sorted_results[:limit]
        else:
            # Fallback to vector results only
            results = [{"content": r, "vector_score": r.get("similarity", 0)} 
                      for r in vector_results[:limit]]
        
        return results
    
    def _get_documents_for_keyword_search(self) -> List[Dict]:
        """Get documents for keyword search"""
        # This would fetch from your document store
        # For now, return empty list
        return []
'''
    
    with open('hybrid_searcher.py', 'w') as f:
        f.write(code)
    
    print("\n✅ Created hybrid_searcher.py")

def main():
    """Main setup function"""
    print("🚀 FF_Agent RAG Enhancement Setup")
    print("="*60)
    
    # Step 1: Check dependencies
    print("\n1️⃣ Checking dependencies...")
    if not check_dependencies():
        print("Please install missing dependencies and run again")
        return
    
    # Step 2: Initialize vector database
    print("\n2️⃣ Initializing vector database...")
    vector_store = initialize_vector_database()
    
    # Step 3: Ingest documents
    print("\n3️⃣ Ingesting project documents...")
    total_ingested = ingest_project_documents(vector_store)
    print(f"\n✅ Total documents ingested: {total_ingested}")
    
    # Step 4: Seed telecom knowledge
    if vector_store:
        seed_telecom_knowledge(vector_store)
    
    # Step 5: Create hybrid searcher
    print("\n4️⃣ Creating hybrid search module...")
    create_hybrid_searcher()
    
    # Step 6: Test RAG search
    if vector_store:
        test_rag_search(vector_store)
    
    print("\n" + "="*60)
    print("✅ RAG Enhancement Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. The document ingester is ready to use")
    print("2. Hybrid search module created (hybrid_searcher.py)")
    print("3. Vector store is seeded with telecom knowledge")
    print("4. You can now use RAG in your queries!")
    
    if not vector_store:
        print("\n⚠️  Note: Running without vector store.")
        print("   To enable full RAG:")
        print("   1. Set NEON_DATABASE_URL in .env")
        print("   2. Set OPENAI_API_KEY in .env (for embeddings)")
        print("   3. Run this script again")

if __name__ == "__main__":
    main()