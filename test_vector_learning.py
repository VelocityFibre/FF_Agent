"""
Test suite for vector database learning and improvement
Uses real data from Neon and Firebase to build query patterns
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import random
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import psycopg2
from vector_store import VectorStore
import google.generativeai as genai

load_dotenv()

class VectorDatabaseTester:
    def __init__(self):
        self.vector_store = VectorStore()
        self.engine = create_engine(os.getenv("NEON_DATABASE_URL"))
        genai.configure(api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        self.test_results = []
        
    def analyze_existing_data(self):
        """Analyze actual data patterns in your database"""
        print("\n📊 Analyzing your actual database content...")
        
        analysis = {
            'tables': {},
            'data_patterns': {},
            'suggested_queries': []
        }
        
        with self.engine.connect() as conn:
            # Get all tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            
            for table in tables:
                print(f"  Analyzing table: {table}")
                
                # Get row count
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                row_count = count_result.scalar()
                
                # Get sample data
                sample_result = conn.execute(text(f"SELECT * FROM {table} LIMIT 5"))
                columns = sample_result.keys()
                
                # Get distinct values for categorical columns
                distinct_values = {}
                for col in columns:
                    try:
                        distinct_result = conn.execute(text(f"""
                            SELECT COUNT(DISTINCT {col}) as distinct_count
                            FROM {table}
                        """))
                        distinct_count = distinct_result.scalar()
                        
                        if distinct_count and distinct_count < 20:  # Likely categorical
                            values_result = conn.execute(text(f"""
                                SELECT DISTINCT {col} 
                                FROM {table} 
                                WHERE {col} IS NOT NULL
                                LIMIT 10
                            """))
                            distinct_values[col] = [row[0] for row in values_result]
                    except:
                        pass  # Skip columns that can't be analyzed
                
                analysis['tables'][table] = {
                    'row_count': row_count,
                    'columns': list(columns),
                    'categorical_columns': distinct_values
                }
                
                # Generate suggested test queries based on actual data
                if 'status' in distinct_values:
                    for status in distinct_values['status']:
                        analysis['suggested_queries'].append(
                            f"Show all {table} with status {status}"
                        )
                
                if 'created_at' in columns or 'date' in columns:
                    analysis['suggested_queries'].append(
                        f"Get {table} from last 30 days"
                    )
                    analysis['suggested_queries'].append(
                        f"Show {table} grouped by month"
                    )
        
        return analysis
    
    def generate_query_variations(self, base_query: str) -> List[str]:
        """Generate variations of a query to test similarity"""
        variations = [base_query]
        
        # Synonym replacements
        synonyms = {
            'show': ['display', 'list', 'get', 'find', 'retrieve'],
            'all': ['every', 'each', 'complete', ''],
            'with': ['having', 'where', 'that have'],
            'last': ['past', 'previous', 'recent'],
            'active': ['enabled', 'current', 'live'],
            'inactive': ['disabled', 'suspended', 'deactivated']
        }
        
        # Generate variations
        for word, syns in synonyms.items():
            if word in base_query.lower():
                for syn in syns:
                    variation = base_query.lower().replace(word, syn)
                    if variation and variation != base_query.lower():
                        variations.append(variation.capitalize())
        
        # Add question forms
        if base_query.startswith("Show"):
            variations.append(f"What are the {base_query[5:]}?")
            variations.append(f"Can you show me {base_query[5:]}?")
        
        return list(set(variations))[:5]  # Return up to 5 unique variations
    
    def test_query_accuracy(self, test_queries: List[Dict]) -> Dict:
        """Test SQL generation accuracy with real queries"""
        print("\n🧪 Testing query generation accuracy...")
        
        results = {
            'total': len(test_queries),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'execution_times': []
        }
        
        for test in test_queries:
            question = test['question']
            expected_pattern = test.get('expected_pattern', '')
            
            try:
                start_time = time.time()
                
                # Get vector context
                context = self.vector_store.get_query_context(question)
                
                # Generate SQL
                prompt = f"""Generate SQL for: {question}
                Use these similar examples: {context['examples'][:2]}
                Return only the SQL query."""
                
                response = self.gemini_model.generate_content(prompt)
                generated_sql = response.text.strip().replace("```sql", "").replace("```", "")
                
                # Test execution
                with self.engine.connect() as conn:
                    result = conn.execute(text(generated_sql))
                    rows = result.fetchall()
                
                execution_time = time.time() - start_time
                
                # Store successful query
                self.vector_store.store_successful_query(
                    question=question,
                    sql_query=generated_sql,
                    execution_time=execution_time
                )
                
                results['successful'] += 1
                results['execution_times'].append(execution_time)
                
                print(f"  ✅ {question[:50]}... ({execution_time:.3f}s)")
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'question': question,
                    'error': str(e)
                })
                
                # Store error pattern
                self.vector_store.store_error_pattern(
                    question=question,
                    attempted_sql=generated_sql if 'generated_sql' in locals() else 'FAILED',
                    error_message=str(e)
                )
                
                print(f"  ❌ {question[:50]}... Error: {str(e)[:50]}")
        
        if results['execution_times']:
            results['avg_execution_time'] = sum(results['execution_times']) / len(results['execution_times'])
        
        return results
    
    def test_similarity_clustering(self) -> Dict:
        """Test how well similar queries cluster together"""
        print("\n🔍 Testing similarity clustering...")
        
        test_groups = [
            {
                'category': 'Customer Status Queries',
                'queries': [
                    "Show active customers",
                    "Display customers with active status",
                    "List all active customers",
                    "Get customers that are currently active",
                    "Which customers have active status"
                ]
            },
            {
                'category': 'Time-based Queries',
                'queries': [
                    "Show orders from last month",
                    "Get orders from the past 30 days",
                    "Display recent orders",
                    "List orders from previous month",
                    "What orders were placed last month"
                ]
            },
            {
                'category': 'Aggregation Queries',
                'queries': [
                    "Get total sales by month",
                    "Show revenue grouped by month",
                    "Calculate monthly sales totals",
                    "Sum sales for each month",
                    "What are the monthly sales figures"
                ]
            }
        ]
        
        clustering_results = {}
        
        for group in test_groups:
            category = group['category']
            queries = group['queries']
            
            print(f"\n  Testing {category}:")
            
            # Store all queries
            for query in queries:
                self.vector_store.store_successful_query(
                    question=query,
                    sql_query=f"SELECT * FROM test -- {category}",
                    execution_time=0.01
                )
            
            # Test retrieval accuracy
            intra_group_similarities = []
            
            for query in queries:
                similar = self.vector_store.find_similar_queries(query, limit=5)
                
                # Check how many of the similar queries are from the same category
                same_category = sum(1 for s in similar if category in s.get('sql_query', ''))
                accuracy = same_category / min(len(similar), len(queries)-1) if similar else 0
                
                intra_group_similarities.append(accuracy)
                print(f"    Query: {query[:40]}... Clustering accuracy: {accuracy:.1%}")
            
            clustering_results[category] = {
                'avg_clustering_accuracy': sum(intra_group_similarities) / len(intra_group_similarities),
                'queries_tested': len(queries)
            }
        
        return clustering_results
    
    def test_learning_improvement(self, iterations: int = 3) -> Dict:
        """Test if the system improves with more data"""
        print("\n📈 Testing learning improvement over iterations...")
        
        improvement_metrics = {
            'iterations': [],
            'baseline_accuracy': 0,
            'final_accuracy': 0
        }
        
        test_queries = [
            "Show customers who ordered this month",
            "Get top selling products",
            "Find orders with high value",
            "List customers by total spending",
            "Show inventory levels"
        ]
        
        for iteration in range(iterations):
            print(f"\n  Iteration {iteration + 1}:")
            
            # Test current accuracy
            correct = 0
            total = len(test_queries)
            
            for query in test_queries:
                variations = self.generate_query_variations(query)
                
                for variant in variations[:2]:  # Test 2 variations
                    similar = self.vector_store.find_similar_queries(variant, limit=1)
                    if similar and similar[0]['similarity'] > 0.8:
                        correct += 1
            
            accuracy = correct / (total * 2)  # 2 variations per query
            improvement_metrics['iterations'].append({
                'iteration': iteration + 1,
                'accuracy': accuracy,
                'total_embeddings': self._count_embeddings()
            })
            
            if iteration == 0:
                improvement_metrics['baseline_accuracy'] = accuracy
            
            print(f"    Accuracy: {accuracy:.1%}")
            print(f"    Total embeddings: {self._count_embeddings()}")
            
            # Add more training data
            for query in test_queries:
                for variant in self.generate_query_variations(query):
                    self.vector_store.store_successful_query(
                        question=variant,
                        sql_query=f"SELECT * FROM table -- training",
                        execution_time=0.05
                    )
        
        improvement_metrics['final_accuracy'] = improvement_metrics['iterations'][-1]['accuracy']
        improvement_metrics['improvement_percentage'] = (
            (improvement_metrics['final_accuracy'] - improvement_metrics['baseline_accuracy']) / 
            improvement_metrics['baseline_accuracy'] * 100
            if improvement_metrics['baseline_accuracy'] > 0 else 0
        )
        
        return improvement_metrics
    
    def test_edge_cases(self) -> Dict:
        """Test edge cases and unusual queries"""
        print("\n⚠️ Testing edge cases...")
        
        edge_cases = [
            {
                'query': "Show customers",  # Ambiguous
                'type': 'ambiguous'
            },
            {
                'query': "Get data from yesterday at 3:45 PM EST",  # Very specific time
                'type': 'specific_time'
            },
            {
                'query': "Find products where price > 100 AND (category = 'Electronics' OR brand IN ('Apple', 'Samsung'))",  # Complex logic
                'type': 'complex_logic'
            },
            {
                'query': "显示所有客户",  # Non-English (Chinese: "Show all customers")
                'type': 'non_english'
            },
            {
                'query': "SHOW CUSTOMERS; DROP TABLE users; --",  # SQL injection attempt
                'type': 'sql_injection'
            }
        ]
        
        results = {
            'total': len(edge_cases),
            'handled': 0,
            'failed': 0,
            'by_type': {}
        }
        
        for case in edge_cases:
            query = case['query']
            case_type = case['type']
            
            try:
                # Try to find similar queries
                similar = self.vector_store.find_similar_queries(query, limit=3)
                
                if similar:
                    print(f"  ✅ {case_type}: Found {len(similar)} similar queries")
                    results['handled'] += 1
                else:
                    print(f"  ⚠️ {case_type}: No similar queries found")
                    results['failed'] += 1
                
                results['by_type'][case_type] = {
                    'query': query[:50],
                    'similar_found': len(similar) if similar else 0,
                    'top_similarity': similar[0]['similarity'] if similar else 0
                }
                
            except Exception as e:
                print(f"  ❌ {case_type}: Error - {str(e)[:50]}")
                results['failed'] += 1
                results['by_type'][case_type] = {
                    'query': query[:50],
                    'error': str(e)[:100]
                }
        
        return results
    
    def _count_embeddings(self) -> int:
        """Count total embeddings in database"""
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM query_embeddings")
                return cur.fetchone()[0]
    
    def run_comprehensive_tests(self):
        """Run all tests and generate report"""
        print("\n" + "="*60)
        print("🚀 COMPREHENSIVE VECTOR DATABASE TESTING")
        print("="*60)
        
        # 1. Analyze existing data
        data_analysis = self.analyze_existing_data()
        print(f"\n✅ Found {len(data_analysis['tables'])} tables to work with")
        
        # 2. Generate test queries from actual data
        test_queries = []
        for suggested in data_analysis['suggested_queries'][:10]:
            test_queries.append({'question': suggested})
        
        # 3. Run tests
        accuracy_results = self.test_query_accuracy(test_queries)
        clustering_results = self.test_similarity_clustering()
        improvement_results = self.test_learning_improvement()
        edge_case_results = self.test_edge_cases()
        
        # 4. Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'data_analysis': {
                'tables_analyzed': len(data_analysis['tables']),
                'total_rows': sum(t['row_count'] for t in data_analysis['tables'].values()),
                'suggested_queries_generated': len(data_analysis['suggested_queries'])
            },
            'accuracy_test': {
                'success_rate': f"{(accuracy_results['successful']/accuracy_results['total']*100):.1f}%" if accuracy_results['total'] > 0 else "0%",
                'avg_execution_time': f"{accuracy_results.get('avg_execution_time', 0):.3f}s"
            },
            'clustering_test': {
                'avg_accuracy': f"{sum(c['avg_clustering_accuracy'] for c in clustering_results.values())/len(clustering_results)*100:.1f}%" if clustering_results else "0%"
            },
            'learning_test': {
                'improvement': f"{improvement_results['improvement_percentage']:.1f}%",
                'final_accuracy': f"{improvement_results['final_accuracy']*100:.1f}%"
            },
            'edge_cases': {
                'handled_rate': f"{(edge_case_results['handled']/edge_case_results['total']*100):.1f}%" if edge_case_results['total'] > 0 else "0%"
            }
        }
        
        # Save report
        with open('vector_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"✅ Query Accuracy: {report['accuracy_test']['success_rate']}")
        print(f"✅ Clustering Accuracy: {report['clustering_test']['avg_accuracy']}")
        print(f"✅ Learning Improvement: {report['learning_test']['improvement']}")
        print(f"✅ Edge Case Handling: {report['edge_cases']['handled_rate']}")
        print(f"\n📁 Full report saved to: vector_test_report.json")
        
        return report

if __name__ == "__main__":
    tester = VectorDatabaseTester()
    report = tester.run_comprehensive_tests()