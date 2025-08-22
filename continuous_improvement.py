"""
Continuous Improvement Pipeline for Vector Database
Orchestrates testing, learning, and optimization automatically
"""

import os
import json
import time
import schedule
from datetime import datetime, timedelta
from typing import Dict, List
from dotenv import load_dotenv

# Import all our testing and learning modules
from test_vector_learning import VectorDatabaseTester
from production_learner import ProductionLearner
from benchmark_vector_performance import VectorPerformanceBenchmark
from vector_store import VectorStore

load_dotenv()

class ContinuousImprovementPipeline:
    def __init__(self):
        self.vector_store = VectorStore()
        self.tester = VectorDatabaseTester()
        self.learner = ProductionLearner()
        self.benchmark = VectorPerformanceBenchmark()
        self.metrics_history = []
        
    def run_daily_improvement_cycle(self):
        """Run daily improvement cycle"""
        print("\n" + "="*70)
        print(f"🔄 DAILY IMPROVEMENT CYCLE - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'steps': {}
        }
        
        try:
            # Step 1: Learn from production data
            print("\n📚 Step 1: Learning from Production Data...")
            learning_results = self.learner.run_learning_cycle()
            cycle_results['steps']['learning'] = {
                'new_patterns': learning_results['total_learned'],
                'total_embeddings': learning_results['total_embeddings']
            }
            
            # Step 2: Test current performance
            print("\n🧪 Step 2: Testing Current Performance...")
            test_results = self._run_quick_tests()
            cycle_results['steps']['testing'] = test_results
            
            # Step 3: Optimize if needed
            print("\n🔧 Step 3: Optimization Check...")
            optimization_results = self._optimize_if_needed(test_results)
            cycle_results['steps']['optimization'] = optimization_results
            
            # Step 4: Update metrics
            print("\n📊 Step 4: Updating Metrics...")
            metrics = self._calculate_metrics()
            cycle_results['metrics'] = metrics
            
            # Save results
            self._save_cycle_results(cycle_results)
            
            # Generate alerts if needed
            self._check_alerts(metrics)
            
            print("\n✅ Daily improvement cycle completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error in improvement cycle: {e}")
            cycle_results['error'] = str(e)
            self._save_cycle_results(cycle_results)
        
        return cycle_results
    
    def run_weekly_deep_analysis(self):
        """Run comprehensive weekly analysis"""
        print("\n" + "="*70)
        print(f"📈 WEEKLY DEEP ANALYSIS - {datetime.now().strftime('%Y-%m-%d')}")
        print("="*70)
        
        analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'type': 'weekly_analysis'
        }
        
        try:
            # Run comprehensive tests
            print("\n1️⃣ Running Comprehensive Tests...")
            test_report = self.tester.run_comprehensive_tests()
            analysis_results['comprehensive_tests'] = test_report
            
            # Run performance benchmarks
            print("\n2️⃣ Running Performance Benchmarks...")
            benchmark_report = self.benchmark.generate_report()
            analysis_results['benchmarks'] = benchmark_report
            
            # Analyze trends
            print("\n3️⃣ Analyzing Weekly Trends...")
            trends = self._analyze_weekly_trends()
            analysis_results['trends'] = trends
            
            # Generate recommendations
            print("\n4️⃣ Generating Recommendations...")
            recommendations = self._generate_weekly_recommendations(
                test_report, benchmark_report, trends
            )
            analysis_results['recommendations'] = recommendations
            
            # Save weekly report
            self._save_weekly_report(analysis_results)
            
            print("\n✅ Weekly analysis completed!")
            print(f"📁 Report saved to: weekly_analysis_{datetime.now().strftime('%Y%m%d')}.json")
            
        except Exception as e:
            print(f"\n❌ Error in weekly analysis: {e}")
            analysis_results['error'] = str(e)
            self._save_weekly_report(analysis_results)
        
        return analysis_results
    
    def _run_quick_tests(self) -> Dict:
        """Run quick performance tests"""
        test_queries = [
            "Show active customers",
            "Get orders from last month",
            "Find top products"
        ]
        
        results = {
            'similarity_accuracy': 0,
            'query_success_rate': 0,
            'avg_search_time': 0
        }
        
        # Test similarity accuracy
        correct = 0
        total_time = 0
        
        for query in test_queries:
            start = time.time()
            similar = self.vector_store.find_similar_queries(query, limit=3)
            elapsed = time.time() - start
            
            if similar and similar[0]['similarity'] > 0.8:
                correct += 1
            
            total_time += elapsed
        
        results['similarity_accuracy'] = (correct / len(test_queries)) * 100
        results['avg_search_time'] = total_time / len(test_queries)
        
        # Get success rate from database
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT AVG(success_rate) FROM query_embeddings")
                avg_success = cur.fetchone()[0]
                results['query_success_rate'] = float(avg_success * 100) if avg_success else 0
        
        return results
    
    def _optimize_if_needed(self, test_results: Dict) -> Dict:
        """Optimize based on test results"""
        optimization_actions = []
        
        # Check if similarity accuracy is low
        if test_results['similarity_accuracy'] < 70:
            print("  ⚠️ Low similarity accuracy detected, adding more training data...")
            self._add_synthetic_training_data()
            optimization_actions.append("Added synthetic training data")
        
        # Check if search is slow
        if test_results['avg_search_time'] > 0.5:
            print("  ⚠️ Slow search detected, optimizing indexes...")
            self._optimize_indexes()
            optimization_actions.append("Optimized database indexes")
        
        # Check if success rate is low
        if test_results['query_success_rate'] < 80:
            print("  ⚠️ Low success rate detected, cleaning poor embeddings...")
            self.learner.optimize_embeddings()
            optimization_actions.append("Cleaned poor quality embeddings")
        
        if not optimization_actions:
            print("  ✅ No optimization needed, performance is good!")
        
        return {
            'actions_taken': optimization_actions,
            'optimized': len(optimization_actions) > 0
        }
    
    def _add_synthetic_training_data(self):
        """Add synthetic training data to improve accuracy"""
        synthetic_queries = [
            ("Find all customers", "SELECT * FROM customers"),
            ("Show recent orders", "SELECT * FROM orders WHERE order_date > CURRENT_DATE - INTERVAL '7 days'"),
            ("Get product inventory", "SELECT product_id, product_name, stock_quantity FROM products"),
            ("Calculate total revenue", "SELECT SUM(total_amount) as revenue FROM orders"),
            ("List pending tasks", "FIREBASE_QUERY: tasks WHERE status = 'pending'")
        ]
        
        for question, sql in synthetic_queries:
            self.vector_store.store_successful_query(
                question=question,
                sql_query=sql,
                execution_time=0.05,
                metadata={'source': 'synthetic', 'created_at': datetime.now().isoformat()}
            )
    
    def _optimize_indexes(self):
        """Optimize database indexes"""
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                # Reindex vector indexes
                cur.execute("REINDEX INDEX query_embedding_idx")
                cur.execute("REINDEX INDEX schema_embedding_idx")
                conn.commit()
    
    def _calculate_metrics(self) -> Dict:
        """Calculate current system metrics"""
        metrics = {}
        
        with self.vector_store.get_connection() as conn:
            with conn.cursor() as cur:
                # Total embeddings
                cur.execute("SELECT COUNT(*) FROM query_embeddings")
                metrics['total_embeddings'] = cur.fetchone()[0]
                
                # Average success rate
                cur.execute("SELECT AVG(success_rate) FROM query_embeddings")
                avg_success = cur.fetchone()[0]
                metrics['avg_success_rate'] = float(avg_success) if avg_success else 0
                
                # Recent queries (last 24 hours)
                cur.execute("""
                    SELECT COUNT(*) FROM query_embeddings 
                    WHERE last_used > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                """)
                metrics['recent_queries'] = cur.fetchone()[0]
                
                # Error rate
                cur.execute("SELECT COUNT(*) FROM error_patterns WHERE resolved = FALSE")
                metrics['unresolved_errors'] = cur.fetchone()[0]
        
        # Add to history
        self.metrics_history.append({
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        })
        
        # Keep only last 30 days
        cutoff = datetime.now() - timedelta(days=30)
        self.metrics_history = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m['timestamp']) > cutoff
        ]
        
        return metrics
    
    def _check_alerts(self, metrics: Dict):
        """Check if any alerts should be triggered"""
        alerts = []
        
        if metrics['avg_success_rate'] < 0.7:
            alerts.append(f"⚠️ ALERT: Success rate below 70% ({metrics['avg_success_rate']:.1%})")
        
        if metrics['unresolved_errors'] > 50:
            alerts.append(f"⚠️ ALERT: {metrics['unresolved_errors']} unresolved errors")
        
        if metrics['recent_queries'] == 0:
            alerts.append("⚠️ ALERT: No queries in last 24 hours")
        
        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
            
            # Save alerts to file
            with open('alerts.log', 'a') as f:
                for alert in alerts:
                    f.write(f"{datetime.now().isoformat()} - {alert}\n")
    
    def _analyze_weekly_trends(self) -> Dict:
        """Analyze trends over the past week"""
        if len(self.metrics_history) < 7:
            return {'status': 'insufficient_data'}
        
        # Get metrics from 7 days ago vs today
        week_ago = self.metrics_history[0]['metrics'] if self.metrics_history else {}
        current = self.metrics_history[-1]['metrics'] if self.metrics_history else {}
        
        trends = {
            'embedding_growth': current.get('total_embeddings', 0) - week_ago.get('total_embeddings', 0),
            'success_rate_change': current.get('avg_success_rate', 0) - week_ago.get('avg_success_rate', 0),
            'query_volume_change': current.get('recent_queries', 0) - week_ago.get('recent_queries', 0)
        }
        
        # Determine trend direction
        trends['overall_trend'] = 'improving' if trends['success_rate_change'] > 0 else 'declining'
        
        return trends
    
    def _generate_weekly_recommendations(self, test_report, benchmark_report, trends) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on trends
        if trends.get('overall_trend') == 'declining':
            recommendations.append("Review and retrain on recent failed queries")
        
        if trends.get('embedding_growth', 0) < 10:
            recommendations.append("Increase learning frequency to capture more patterns")
        
        # Based on benchmarks
        if benchmark_report and 'performance_metrics' in benchmark_report:
            metrics = benchmark_report['performance_metrics']
            
            if float(metrics['accuracy']['improvement'].replace('%', '').replace('+', '')) < 10:
                recommendations.append("Add more diverse training examples")
            
            if float(metrics['efficiency']['token_savings'].replace('%', '')) < 20:
                recommendations.append("Optimize prompt templates for better efficiency")
        
        # Based on tests
        if test_report and 'accuracy_test' in test_report:
            if test_report['accuracy_test']['success_rate'].replace('%', '') < '80':
                recommendations.append("Focus on improving query accuracy through targeted training")
        
        if not recommendations:
            recommendations.append("System performing well - maintain current configuration")
        
        return recommendations
    
    def _save_cycle_results(self, results: Dict):
        """Save daily cycle results"""
        filename = 'daily_improvements.json'
        
        try:
            with open(filename, 'r') as f:
                history = json.load(f)
        except:
            history = []
        
        history.append(results)
        
        # Keep only last 30 days
        if len(history) > 30:
            history = history[-30:]
        
        with open(filename, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _save_weekly_report(self, report: Dict):
        """Save weekly analysis report"""
        filename = f"weekly_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
    
    def start_continuous_improvement(self):
        """Start the continuous improvement pipeline"""
        print("🚀 Starting Continuous Improvement Pipeline")
        print("="*50)
        print("Schedule:")
        print("  • Daily: Learning + Testing + Optimization")
        print("  • Weekly: Deep Analysis + Benchmarks")
        print("="*50)
        
        # Run initial cycle
        self.run_daily_improvement_cycle()
        
        # Schedule daily runs at 2 AM
        schedule.every().day.at("02:00").do(self.run_daily_improvement_cycle)
        
        # Schedule weekly runs on Sundays at 3 AM
        schedule.every().sunday.at("03:00").do(self.run_weekly_deep_analysis)
        
        print("\n✅ Pipeline scheduled. Press Ctrl+C to stop.")
        print("📊 Monitoring dashboard available at: http://localhost:8000/metrics")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    pipeline = ContinuousImprovementPipeline()
    
    # Run once for testing
    print("Running single improvement cycle for testing...")
    pipeline.run_daily_improvement_cycle()
    
    # Uncomment to start continuous improvement
    # pipeline.start_continuous_improvement()