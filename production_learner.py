"""
Production Learning System for Vector Database
Automatically learns from real query patterns in your Neon/Firebase data
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import firebase_admin
from firebase_admin import credentials, firestore
from vector_store import VectorStore
import schedule
import time

load_dotenv()

class ProductionLearner:
    def __init__(self):
        self.vector_store = VectorStore()
        self.engine = create_engine(os.getenv("NEON_DATABASE_URL"))
        self.processed_queries = set()  # Track processed queries to avoid duplicates
        self._init_firebase()
        
    def _init_firebase(self):
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate('firebase-credentials.json')
                firebase_admin.initialize_app(cred)
            self.firestore_db = firestore.client()
        except Exception as e:
            print(f"Firebase initialization failed: {e}")
            self.firestore_db = None
    
    def extract_neon_query_patterns(self) -> List[Dict]:
        """Extract common query patterns from Neon data"""
        print("🔍 Extracting query patterns from Neon...")
        
        patterns = []
        
        with self.engine.connect() as conn:
            # Get tables from information schema (more compatible)
            table_stats = conn.execute(text("""
                SELECT 
                    table_name,
                    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)).fetchall()
            
            for stat in table_stats:
                table = stat[0]  # table_name is first column
                
                # Check if table has data
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table} LIMIT 1"))
                    row_count = count_result.scalar()
                    
                    if row_count and row_count > 0:
                        # Generate patterns based on table
                        patterns.extend(self._generate_table_patterns(table, conn))
                except Exception as e:
                    print(f"  Skipping table {table}: {e}")
                    continue
        
        return patterns
    
    def _generate_table_patterns(self, table: str, conn) -> List[Dict]:
        """Generate query patterns for a specific table"""
        patterns = []
        
        try:
            # Get table columns
            columns_result = conn.execute(text(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """))
            columns = {row[0]: row[1] for row in columns_result}
            
            # Pattern 1: Select all
            patterns.append({
                'question': f"Show all {table}",
                'sql': f"SELECT * FROM {table}",
                'confidence': 1.0
            })
            
            # Pattern 2: Count
            patterns.append({
                'question': f"How many {table} are there",
                'sql': f"SELECT COUNT(*) as count FROM {table}",
                'confidence': 1.0
            })
            
            # Pattern 3: Status-based queries (if status column exists)
            if 'status' in columns:
                # Get distinct statuses
                status_result = conn.execute(text(f"""
                    SELECT DISTINCT status 
                    FROM {table} 
                    WHERE status IS NOT NULL 
                    LIMIT 5
                """))
                statuses = [row[0] for row in status_result]
                
                for status in statuses:
                    patterns.append({
                        'question': f"Show {table} with {status} status",
                        'sql': f"SELECT * FROM {table} WHERE status = '{status}'",
                        'confidence': 0.9
                    })
            
            # Pattern 4: Date-based queries (if date columns exist)
            date_columns = [col for col in columns if 'date' in col.lower() or 'time' in col.lower()]
            for date_col in date_columns:
                patterns.append({
                    'question': f"Show recent {table}",
                    'sql': f"SELECT * FROM {table} WHERE {date_col} >= CURRENT_DATE - INTERVAL '30 days'",
                    'confidence': 0.8
                })
                
                patterns.append({
                    'question': f"Get {table} from last month",
                    'sql': f"""SELECT * FROM {table} 
                              WHERE {date_col} >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
                              AND {date_col} < DATE_TRUNC('month', CURRENT_DATE)""",
                    'confidence': 0.8
                })
            
            # Pattern 5: Aggregations (if numeric columns exist)
            numeric_columns = [col for col, dtype in columns.items() 
                             if dtype in ['integer', 'numeric', 'real', 'double precision']]
            
            for num_col in numeric_columns[:2]:  # Limit to avoid too many patterns
                patterns.append({
                    'question': f"What is the total {num_col} in {table}",
                    'sql': f"SELECT SUM({num_col}) as total FROM {table}",
                    'confidence': 0.7
                })
                
                patterns.append({
                    'question': f"What is the average {num_col} in {table}",
                    'sql': f"SELECT AVG({num_col}) as average FROM {table}",
                    'confidence': 0.7
                })
            
            # Pattern 6: Top N queries
            if 'name' in columns or 'title' in columns:
                order_col = 'created_at' if 'created_at' in columns else list(columns.keys())[0]
                patterns.append({
                    'question': f"Show top 10 {table}",
                    'sql': f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT 10",
                    'confidence': 0.8
                })
            
        except Exception as e:
            print(f"  Error generating patterns for {table}: {e}")
        
        return patterns
    
    def extract_firebase_patterns(self) -> List[Dict]:
        """Extract query patterns from Firebase collections"""
        if not self.firestore_db:
            return []
        
        print("🔥 Extracting patterns from Firebase...")
        patterns = []
        
        # Common Firebase collections to analyze
        collections = ['users', 'meetings', 'tasks', 'actionItemsManagement']
        
        for collection_name in collections:
            try:
                # Get sample documents
                docs = self.firestore_db.collection(collection_name).limit(5).get()
                
                if docs:
                    # Analyze document structure
                    sample_doc = docs[0].to_dict()
                    fields = list(sample_doc.keys())
                    
                    # Generate patterns
                    patterns.append({
                        'question': f"Show all {collection_name}",
                        'sql': f"FIREBASE_QUERY: {collection_name}",
                        'confidence': 1.0
                    })
                    
                    # Field-specific patterns
                    if 'status' in fields:
                        patterns.append({
                            'question': f"Show {collection_name} with pending status",
                            'sql': f"FIREBASE_QUERY: {collection_name} WHERE status = 'pending'",
                            'confidence': 0.8
                        })
                    
                    if 'assignee' in fields:
                        patterns.append({
                            'question': f"Show {collection_name} assigned to someone",
                            'sql': f"FIREBASE_QUERY: {collection_name} WHERE assignee != null",
                            'confidence': 0.7
                        })
                    
                    if 'createdAt' in fields or 'timestamp' in fields:
                        patterns.append({
                            'question': f"Show recent {collection_name}",
                            'sql': f"FIREBASE_QUERY: {collection_name} ORDER BY createdAt DESC LIMIT 50",
                            'confidence': 0.8
                        })
                    
            except Exception as e:
                print(f"  Error analyzing Firebase collection {collection_name}: {e}")
        
        return patterns
    
    def learn_from_patterns(self, patterns: List[Dict], source: str = "auto"):
        """Store discovered patterns in vector database"""
        print(f"\n📚 Learning {len(patterns)} patterns from {source}...")
        
        learned = 0
        skipped = 0
        
        for pattern in patterns:
            # Create unique hash for this pattern to avoid duplicates
            pattern_hash = hashlib.md5(
                f"{pattern['question']}:{pattern['sql']}".encode()
            ).hexdigest()
            
            if pattern_hash not in self.processed_queries:
                try:
                    # Store in vector database with confidence weighting
                    self.vector_store.store_successful_query(
                        question=pattern['question'],
                        sql_query=pattern['sql'],
                        execution_time=0.01,  # Simulated fast execution
                        metadata={
                            'source': source,
                            'confidence': pattern.get('confidence', 0.5),
                            'learned_at': datetime.now().isoformat()
                        }
                    )
                    
                    self.processed_queries.add(pattern_hash)
                    learned += 1
                    
                except Exception as e:
                    print(f"  Error learning pattern: {e}")
            else:
                skipped += 1
        
        print(f"  ✅ Learned: {learned} new patterns")
        print(f"  ⏭️ Skipped: {skipped} duplicate patterns")
        
        return {'learned': learned, 'skipped': skipped}
    
    def analyze_query_logs(self, log_file: Optional[str] = None):
        """Analyze query logs if available"""
        # This would analyze actual query logs if you have them
        # For now, it's a placeholder for future implementation
        pass
    
    def optimize_embeddings(self):
        """Optimize existing embeddings by removing low-quality ones"""
        print("\n🔧 Optimizing embeddings...")
        
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                # Remove queries with very low success rates
                cur.execute("""
                    DELETE FROM query_embeddings
                    WHERE success_rate < 0.3
                    AND execution_count < 3
                """)
                removed_low_quality = cur.rowcount
                
                # Remove very old, unused queries
                cur.execute("""
                    DELETE FROM query_embeddings
                    WHERE last_used < CURRENT_DATE - INTERVAL '90 days'
                    AND execution_count < 5
                """)
                removed_old = cur.rowcount
                
                # Update success rates based on recent performance
                cur.execute("""
                    UPDATE query_embeddings
                    SET success_rate = success_rate * 0.95
                    WHERE last_used < CURRENT_DATE - INTERVAL '30 days'
                """)
                decayed = cur.rowcount
                
                conn.commit()
                
                print(f"  ✅ Removed {removed_low_quality} low-quality embeddings")
                print(f"  ✅ Removed {removed_old} old unused embeddings")
                print(f"  ✅ Decayed {decayed} older embeddings")
    
    def run_learning_cycle(self):
        """Run a complete learning cycle"""
        print("\n" + "="*60)
        print(f"🤖 PRODUCTION LEARNING CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'neon_patterns': 0,
            'firebase_patterns': 0,
            'total_learned': 0
        }
        
        # Extract and learn from Neon
        neon_patterns = self.extract_neon_query_patterns()
        if neon_patterns:
            neon_result = self.learn_from_patterns(neon_patterns, source="neon")
            results['neon_patterns'] = neon_result['learned']
        
        # Extract and learn from Firebase
        firebase_patterns = self.extract_firebase_patterns()
        if firebase_patterns:
            firebase_result = self.learn_from_patterns(firebase_patterns, source="firebase")
            results['firebase_patterns'] = firebase_result['learned']
        
        # Optimize embeddings
        self.optimize_embeddings()
        
        # Calculate totals
        results['total_learned'] = results['neon_patterns'] + results['firebase_patterns']
        
        # Get current stats
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM query_embeddings")
                results['total_embeddings'] = cur.fetchone()[0]
                
                cur.execute("SELECT AVG(success_rate) FROM query_embeddings")
                avg_success = cur.fetchone()[0]
                results['avg_success_rate'] = float(avg_success) if avg_success else 0
        
        # Save results
        log_file = 'learning_log.json'
        try:
            with open(log_file, 'r') as f:
                logs = json.load(f)
        except:
            logs = []
        
        logs.append(results)
        
        # Keep only last 100 logs
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        
        print(f"\n📊 Learning Summary:")
        print(f"  • Learned {results['total_learned']} new patterns")
        print(f"  • Total embeddings: {results['total_embeddings']}")
        print(f"  • Average success rate: {results['avg_success_rate']:.1%}")
        
        return results
    
    def schedule_continuous_learning(self, interval_hours: int = 24):
        """Schedule continuous learning cycles"""
        print(f"📅 Scheduling learning cycles every {interval_hours} hours...")
        
        # Run immediately
        self.run_learning_cycle()
        
        # Schedule future runs
        schedule.every(interval_hours).hours.do(self.run_learning_cycle)
        
        print("✅ Continuous learning scheduled. Press Ctrl+C to stop.")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    learner = ProductionLearner()
    
    # Run once
    learner.run_learning_cycle()
    
    # Or run continuously (uncomment to enable)
    # learner.schedule_continuous_learning(interval_hours=24)