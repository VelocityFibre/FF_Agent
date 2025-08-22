"""
Performance Benchmarking for Vector Database
Measures speed, accuracy, and resource usage improvements
"""

import os
import time
import json
import psutil
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from vector_store import VectorStore
import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd

load_dotenv()

class VectorPerformanceBenchmark:
    def __init__(self):
        self.vector_store = VectorStore()
        self.engine = create_engine(os.getenv("NEON_DATABASE_URL"))
        genai.configure(api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        self.results = []
        
    def benchmark_query_speed(self, test_queries: List[str], iterations: int = 3) -> Dict:
        """Compare query generation speed with and without vector assistance"""
        print("\n⚡ Benchmarking Query Speed...")
        
        results = {
            'with_vector': [],
            'without_vector': [],
            'speedup': 0
        }
        
        for query in test_queries:
            print(f"\n  Testing: {query[:50]}...")
            
            # Test WITH vector assistance
            with_vector_times = []
            for _ in range(iterations):
                start = time.time()
                
                # Get vector context
                context = self.vector_store.get_query_context(query)
                
                # Generate SQL with context
                prompt = f"""Generate SQL for: {query}
                Similar examples: {context['examples'][:2]}
                Relevant tables: {context['schema_hints']}
                Return only SQL."""
                
                response = self.gemini_model.generate_content(prompt)
                
                with_vector_times.append(time.time() - start)
            
            # Test WITHOUT vector assistance
            without_vector_times = []
            for _ in range(iterations):
                start = time.time()
                
                # Generate SQL without context
                prompt = f"""Generate SQL for: {query}
                Use standard database schema.
                Return only SQL."""
                
                response = self.gemini_model.generate_content(prompt)
                
                without_vector_times.append(time.time() - start)
            
            avg_with = np.mean(with_vector_times)
            avg_without = np.mean(without_vector_times)
            
            results['with_vector'].append(avg_with)
            results['without_vector'].append(avg_without)
            
            speedup = ((avg_without - avg_with) / avg_without) * 100 if avg_without > 0 else 0
            print(f"    With vector: {avg_with:.3f}s")
            print(f"    Without vector: {avg_without:.3f}s")
            print(f"    Speedup: {speedup:.1f}%")
        
        results['speedup'] = np.mean([
            ((w - v) / w * 100) for w, v in zip(results['without_vector'], results['with_vector'])
            if w > 0
        ])
        
        return results
    
    def benchmark_accuracy(self, test_cases: List[Dict]) -> Dict:
        """Measure accuracy improvements with vector assistance"""
        print("\n🎯 Benchmarking Accuracy...")
        
        results = {
            'with_vector': {'correct': 0, 'total': 0},
            'without_vector': {'correct': 0, 'total': 0}
        }
        
        for case in test_cases:
            question = case['question']
            expected_tables = case.get('expected_tables', [])
            expected_conditions = case.get('expected_conditions', [])
            
            print(f"\n  Testing: {question[:50]}...")
            
            # Test WITH vector
            try:
                context = self.vector_store.get_query_context(question)
                prompt = f"""Generate SQL for: {question}
                Examples: {context['examples'][:1]}
                Return only SQL."""
                
                response = self.gemini_model.generate_content(prompt)
                sql_with_vector = response.text.strip()
                
                # Check accuracy
                correct = all(table in sql_with_vector.lower() for table in expected_tables)
                correct = correct and all(cond in sql_with_vector.lower() for cond in expected_conditions)
                
                if correct:
                    results['with_vector']['correct'] += 1
                results['with_vector']['total'] += 1
                
            except Exception as e:
                print(f"    Error with vector: {e}")
                results['with_vector']['total'] += 1
            
            # Test WITHOUT vector
            try:
                prompt = f"""Generate SQL for: {question}
                Return only SQL."""
                
                response = self.gemini_model.generate_content(prompt)
                sql_without_vector = response.text.strip()
                
                # Check accuracy
                correct = all(table in sql_without_vector.lower() for table in expected_tables)
                correct = correct and all(cond in sql_without_vector.lower() for cond in expected_conditions)
                
                if correct:
                    results['without_vector']['correct'] += 1
                results['without_vector']['total'] += 1
                
            except Exception as e:
                print(f"    Error without vector: {e}")
                results['without_vector']['total'] += 1
        
        # Calculate accuracy percentages
        results['with_vector']['accuracy'] = (
            results['with_vector']['correct'] / results['with_vector']['total'] * 100
            if results['with_vector']['total'] > 0 else 0
        )
        
        results['without_vector']['accuracy'] = (
            results['without_vector']['correct'] / results['without_vector']['total'] * 100
            if results['without_vector']['total'] > 0 else 0
        )
        
        results['improvement'] = results['with_vector']['accuracy'] - results['without_vector']['accuracy']
        
        print(f"\n  With vector: {results['with_vector']['accuracy']:.1f}% accurate")
        print(f"  Without vector: {results['without_vector']['accuracy']:.1f}% accurate")
        print(f"  Improvement: +{results['improvement']:.1f}%")
        
        return results
    
    def benchmark_scalability(self, sizes: List[int] = [100, 500, 1000, 5000]) -> Dict:
        """Test how performance scales with database size"""
        print("\n📈 Benchmarking Scalability...")
        
        results = {
            'sizes': sizes,
            'search_times': [],
            'memory_usage': []
        }
        
        original_count = self._get_embedding_count()
        
        for size in sizes:
            print(f"\n  Testing with {size} embeddings...")
            
            # Add dummy embeddings to reach target size
            current_count = self._get_embedding_count()
            to_add = max(0, size - current_count)
            
            if to_add > 0:
                self._add_dummy_embeddings(to_add)
            
            # Measure search time
            test_query = "Show active customers with recent orders"
            search_times = []
            
            for _ in range(3):
                start = time.time()
                results_found = self.vector_store.find_similar_queries(test_query, limit=10)
                search_times.append(time.time() - start)
            
            avg_search_time = np.mean(search_times)
            results['search_times'].append(avg_search_time)
            
            # Measure memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            results['memory_usage'].append(memory_mb)
            
            print(f"    Search time: {avg_search_time:.3f}s")
            print(f"    Memory usage: {memory_mb:.1f} MB")
        
        # Clean up dummy embeddings
        self._cleanup_dummy_embeddings(original_count)
        
        return results
    
    def benchmark_token_usage(self, test_queries: List[str]) -> Dict:
        """Compare token usage with and without vector context"""
        print("\n💰 Benchmarking Token Usage...")
        
        results = {
            'with_vector': [],
            'without_vector': [],
            'savings': 0
        }
        
        for query in test_queries:
            # With vector - shorter prompt due to examples
            context = self.vector_store.get_query_context(query)
            prompt_with_vector = f"""Generate SQL for: {query}
            Example: {context['examples'][0] if context['examples'] else 'None'}
            Tables: {context['schema_hints'][:2]}"""
            
            tokens_with = len(prompt_with_vector.split())  # Rough approximation
            
            # Without vector - needs full schema
            prompt_without_vector = f"""Generate SQL for: {query}
            Full database schema:
            - customers table with columns: id, name, email, status, created_at
            - orders table with columns: id, customer_id, total, status, created_at
            - products table with columns: id, name, price, category
            - order_items table with columns: order_id, product_id, quantity, price
            Consider all possible joins and conditions."""
            
            tokens_without = len(prompt_without_vector.split())
            
            results['with_vector'].append(tokens_with)
            results['without_vector'].append(tokens_without)
            
            print(f"\n  Query: {query[:40]}...")
            print(f"    With vector: ~{tokens_with} tokens")
            print(f"    Without vector: ~{tokens_without} tokens")
            print(f"    Saved: {tokens_without - tokens_with} tokens")
        
        total_with = sum(results['with_vector'])
        total_without = sum(results['without_vector'])
        results['savings'] = ((total_without - total_with) / total_without * 100) if total_without > 0 else 0
        
        print(f"\n  Total savings: {results['savings']:.1f}% fewer tokens")
        
        return results
    
    def benchmark_learning_curve(self, training_queries: List[str], test_queries: List[str]) -> Dict:
        """Measure how quickly the system learns and improves"""
        print("\n📚 Benchmarking Learning Curve...")
        
        results = {
            'training_steps': [],
            'accuracy_progression': []
        }
        
        # Start with empty knowledge
        initial_count = self._get_embedding_count()
        
        # Test initial accuracy
        initial_accuracy = self._test_accuracy(test_queries)
        results['training_steps'].append(0)
        results['accuracy_progression'].append(initial_accuracy)
        
        # Progressively train and test
        batch_size = len(training_queries) // 4
        for i in range(4):
            # Train on batch
            batch = training_queries[i*batch_size:(i+1)*batch_size]
            for query in batch:
                self.vector_store.store_successful_query(
                    question=query,
                    sql_query=f"SELECT * FROM test -- training",
                    execution_time=0.01
                )
            
            # Test accuracy
            accuracy = self._test_accuracy(test_queries)
            results['training_steps'].append((i+1)*batch_size)
            results['accuracy_progression'].append(accuracy)
            
            print(f"  After {(i+1)*batch_size} training queries: {accuracy:.1f}% accuracy")
        
        # Calculate learning rate
        if len(results['accuracy_progression']) > 1:
            improvements = [results['accuracy_progression'][i+1] - results['accuracy_progression'][i] 
                          for i in range(len(results['accuracy_progression'])-1)]
            results['avg_improvement_per_step'] = np.mean(improvements)
        else:
            results['avg_improvement_per_step'] = 0
        
        return results
    
    def _get_embedding_count(self) -> int:
        """Get current number of embeddings"""
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM query_embeddings")
                return cur.fetchone()[0]
    
    def _add_dummy_embeddings(self, count: int):
        """Add dummy embeddings for testing"""
        for i in range(count):
            self.vector_store.store_successful_query(
                question=f"Dummy query {i} for benchmarking",
                sql_query=f"SELECT * FROM dummy_{i}",
                execution_time=0.001
            )
    
    def _cleanup_dummy_embeddings(self, target_count: int):
        """Remove dummy embeddings"""
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM query_embeddings 
                    WHERE question LIKE 'Dummy query%'
                """)
                conn.commit()
    
    def _test_accuracy(self, queries: List[str]) -> float:
        """Test accuracy on a set of queries"""
        correct = 0
        for query in queries:
            similar = self.vector_store.find_similar_queries(query, limit=1)
            if similar and similar[0]['similarity'] > 0.8:
                correct += 1
        return (correct / len(queries) * 100) if queries else 0
    
    def generate_report(self, output_file: str = "benchmark_report.json"):
        """Generate comprehensive benchmark report"""
        print("\n" + "="*60)
        print("🏆 COMPREHENSIVE PERFORMANCE BENCHMARK")
        print("="*60)
        
        # Prepare test data
        test_queries = [
            "Show all active customers",
            "Get orders from last month",
            "Find top selling products",
            "List customers by total spending",
            "Show inventory levels"
        ]
        
        test_cases = [
            {
                'question': "Show active customers",
                'expected_tables': ['customers'],
                'expected_conditions': ['status', 'active']
            },
            {
                'question': "Get total sales by month",
                'expected_tables': ['orders'],
                'expected_conditions': ['sum', 'group by']
            }
        ]
        
        training_queries = [f"Query variation {i}" for i in range(20)]
        
        # Run all benchmarks
        speed_results = self.benchmark_query_speed(test_queries[:3])
        accuracy_results = self.benchmark_accuracy(test_cases)
        scalability_results = self.benchmark_scalability([100, 500, 1000])
        token_results = self.benchmark_token_usage(test_queries[:3])
        learning_results = self.benchmark_learning_curve(training_queries, test_queries)
        
        # Compile report
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_metrics': {
                'speed': {
                    'average_speedup': f"{speed_results['speedup']:.1f}%",
                    'with_vector_avg': f"{np.mean(speed_results['with_vector']):.3f}s",
                    'without_vector_avg': f"{np.mean(speed_results['without_vector']):.3f}s"
                },
                'accuracy': {
                    'with_vector': f"{accuracy_results['with_vector']['accuracy']:.1f}%",
                    'without_vector': f"{accuracy_results['without_vector']['accuracy']:.1f}%",
                    'improvement': f"+{accuracy_results['improvement']:.1f}%"
                },
                'scalability': {
                    'tested_sizes': scalability_results['sizes'],
                    'search_times': [f"{t:.3f}s" for t in scalability_results['search_times']],
                    'scales_well': scalability_results['search_times'][-1] < scalability_results['search_times'][0] * 10
                },
                'efficiency': {
                    'token_savings': f"{token_results['savings']:.1f}%",
                    'cost_reduction_estimate': f"{token_results['savings'] * 0.8:.1f}%"  # Rough cost estimate
                },
                'learning': {
                    'improvement_rate': f"{learning_results['avg_improvement_per_step']:.2f}% per batch",
                    'final_accuracy': f"{learning_results['accuracy_progression'][-1]:.1f}%"
                }
            },
            'recommendations': self._generate_recommendations(
                speed_results, accuracy_results, scalability_results
            )
        }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n📊 BENCHMARK SUMMARY")
        print("-" * 40)
        print(f"✅ Speed Improvement: {report['performance_metrics']['speed']['average_speedup']}")
        print(f"✅ Accuracy Improvement: {report['performance_metrics']['accuracy']['improvement']}")
        print(f"✅ Token Savings: {report['performance_metrics']['efficiency']['token_savings']}")
        print(f"✅ Learning Rate: {report['performance_metrics']['learning']['improvement_rate']}")
        print(f"\n📁 Full report saved to: {output_file}")
        
        return report
    
    def _generate_recommendations(self, speed, accuracy, scalability) -> List[str]:
        """Generate performance recommendations based on results"""
        recommendations = []
        
        if speed['speedup'] < 20:
            recommendations.append("Consider caching more frequent queries for better speed")
        
        if accuracy['improvement'] < 10:
            recommendations.append("Add more training examples to improve accuracy")
        
        if scalability['search_times'][-1] > 1.0:
            recommendations.append("Consider implementing index optimization for large-scale searches")
        
        recommendations.append("Continue monitoring and learning from production queries")
        
        return recommendations

if __name__ == "__main__":
    benchmark = VectorPerformanceBenchmark()
    report = benchmark.generate_report()