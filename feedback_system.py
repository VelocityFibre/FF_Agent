#!/usr/bin/env python3
"""
Feedback Collection and Learning System for FF_Agent
Simplified version for API integration
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from collections import defaultdict, Counter
import uuid
import logging

logger = logging.getLogger(__name__)

class FeedbackSystem:
    """Simplified feedback system for API integration"""
    
    def __init__(self, data_dir: str = "feedback_data"):
        """Initialize feedback system with persistent storage"""
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        self.queries_file = os.path.join(data_dir, "queries.jsonl")
        self.feedback_file = os.path.join(data_dir, "feedback.jsonl")
        self.stats_file = os.path.join(data_dir, "stats.json")
        
        # Load or initialize stats
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load statistics from file"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "feedback_received": 0,
            "positive_feedback": 0,
            "negative_feedback": 0,
            "corrections_received": 0,
            "methods_used": {},
            "average_confidence": 0
        }
    
    def _save_stats(self):
        """Save statistics to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def log_query(self, question: str, sql: Optional[str], success: bool, 
                  method: Optional[str] = None, error: Optional[str] = None) -> str:
        """Log a query execution"""
        query_id = str(uuid.uuid4())
        
        query_data = {
            "query_id": query_id,
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "sql": sql,
            "success": success,
            "method": method,
            "error": error
        }
        
        # Append to queries file
        with open(self.queries_file, 'a') as f:
            f.write(json.dumps(query_data) + '\n')
        
        # Update stats
        self.stats["total_queries"] += 1
        if success:
            self.stats["successful_queries"] += 1
        else:
            self.stats["failed_queries"] += 1
        
        if method:
            if method not in self.stats["methods_used"]:
                self.stats["methods_used"][method] = 0
            self.stats["methods_used"][method] += 1
        
        self._save_stats()
        
        return query_id
    
    def record_feedback(self, query_id: str, was_correct: bool, 
                       feedback: Optional[str] = None, 
                       corrected_sql: Optional[str] = None):
        """Record user feedback for a query"""
        feedback_data = {
            "feedback_id": str(uuid.uuid4()),
            "query_id": query_id,
            "timestamp": datetime.now().isoformat(),
            "was_correct": was_correct,
            "feedback": feedback,
            "corrected_sql": corrected_sql
        }
        
        # Append to feedback file
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(feedback_data) + '\n')
        
        # Update stats
        self.stats["feedback_received"] += 1
        if was_correct:
            self.stats["positive_feedback"] += 1
        else:
            self.stats["negative_feedback"] += 1
        
        if corrected_sql:
            self.stats["corrections_received"] += 1
        
        self._save_stats()
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        # Calculate success rate
        if self.stats["total_queries"] > 0:
            self.stats["success_rate"] = (
                self.stats["successful_queries"] / self.stats["total_queries"]
            ) * 100
        else:
            self.stats["success_rate"] = 0
        
        # Calculate feedback rate
        if self.stats["feedback_received"] > 0:
            self.stats["positive_rate"] = (
                self.stats["positive_feedback"] / self.stats["feedback_received"]
            ) * 100
        else:
            self.stats["positive_rate"] = 0
        
        return self.stats

@dataclass
class QueryFeedback:
    """Structure for query feedback data"""
    query_id: str
    question: str
    sql_generated: str
    entities_detected: Dict
    classification: Dict
    execution_time: float
    row_count: int
    user_feedback: str  # 'positive', 'negative', 'neutral'
    error_message: Optional[str] = None
    correction: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.query_id:
            self.query_id = self.generate_id()
    
    def generate_id(self) -> str:
        """Generate unique ID for query"""
        content = f"{self.question}{self.timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

class FeedbackCollector:
    """Collects and stores user feedback on queries"""
    
    def __init__(self, storage_path: str = "feedback_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # File paths
        self.feedback_file = self.storage_path / "feedback_log.jsonl"
        self.patterns_file = self.storage_path / "learned_patterns.json"
        self.metrics_file = self.storage_path / "metrics.json"
        
        # In-memory cache
        self.recent_feedback = []
        self.learned_patterns = self.load_patterns()
        self.metrics = self.load_metrics()
    
    def load_patterns(self) -> Dict:
        """Load learned patterns from disk"""
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                return json.load(f)
        return {
            'successful_patterns': [],
            'error_patterns': [],
            'entity_mappings': {},
            'routing_rules': {}
        }
    
    def load_metrics(self) -> Dict:
        """Load metrics from disk"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                return json.load(f)
        return {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'corrected_queries': 0,
            'avg_execution_time': 0,
            'feedback_counts': {'positive': 0, 'negative': 0, 'neutral': 0}
        }
    
    def save_patterns(self):
        """Save learned patterns to disk"""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.learned_patterns, f, indent=2)
    
    def save_metrics(self):
        """Save metrics to disk"""
        with open(self.metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)
    
    def collect_feedback(self, 
                         question: str,
                         sql_generated: str,
                         entities_detected: Dict,
                         classification: Dict,
                         execution_time: float,
                         row_count: int,
                         user_feedback: str,
                         error_message: Optional[str] = None,
                         correction: Optional[str] = None) -> QueryFeedback:
        """
        Collect feedback for a query
        
        Args:
            question: Original user question
            sql_generated: SQL that was generated
            entities_detected: Entities found in query
            classification: Query classification
            execution_time: Time to execute query
            row_count: Number of rows returned
            user_feedback: 'positive', 'negative', or 'neutral'
            error_message: Error if query failed
            correction: User-provided correction
        
        Returns:
            QueryFeedback object
        """
        feedback = QueryFeedback(
            query_id="",
            question=question,
            sql_generated=sql_generated,
            entities_detected=entities_detected,
            classification=classification,
            execution_time=execution_time,
            row_count=row_count,
            user_feedback=user_feedback,
            error_message=error_message,
            correction=correction
        )
        
        # Store feedback
        self.store_feedback(feedback)
        
        # Update metrics
        self.update_metrics(feedback)
        
        # Learn from feedback
        self.learn_from_feedback(feedback)
        
        return feedback
    
    def store_feedback(self, feedback: QueryFeedback):
        """Store feedback to disk"""
        # Append to JSONL file
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(asdict(feedback)) + '\n')
        
        # Add to recent cache
        self.recent_feedback.append(feedback)
        
        # Keep only last 100 in memory
        if len(self.recent_feedback) > 100:
            self.recent_feedback.pop(0)
    
    def update_metrics(self, feedback: QueryFeedback):
        """Update metrics based on feedback"""
        self.metrics['total_queries'] += 1
        
        if feedback.user_feedback == 'positive':
            self.metrics['successful_queries'] += 1
        elif feedback.error_message:
            self.metrics['failed_queries'] += 1
        
        if feedback.correction:
            self.metrics['corrected_queries'] += 1
        
        # Update average execution time
        current_avg = self.metrics['avg_execution_time']
        total = self.metrics['total_queries']
        self.metrics['avg_execution_time'] = (
            (current_avg * (total - 1) + feedback.execution_time) / total
        )
        
        # Update feedback counts
        self.metrics['feedback_counts'][feedback.user_feedback] += 1
        
        self.save_metrics()
    
    def learn_from_feedback(self, feedback: QueryFeedback):
        """Learn patterns from feedback"""
        
        if feedback.user_feedback == 'positive':
            # Learn successful patterns
            self._learn_success_pattern(feedback)
        elif feedback.user_feedback == 'negative':
            # Learn error patterns
            self._learn_error_pattern(feedback)
        
        if feedback.correction:
            # Learn from corrections
            self._learn_from_correction(feedback)
        
        self.save_patterns()
    
    def _learn_success_pattern(self, feedback: QueryFeedback):
        """Learn from successful query"""
        pattern = {
            'entities': list(feedback.entities_detected.keys()),
            'classification': feedback.classification.get('type'),
            'databases': feedback.classification.get('databases', []),
            'sql_pattern': self._extract_sql_pattern(feedback.sql_generated),
            'performance': {
                'execution_time': feedback.execution_time,
                'row_count': feedback.row_count
            }
        }
        
        # Add to successful patterns
        self.learned_patterns['successful_patterns'].append(pattern)
        
        # Update entity mappings
        for entity_type, entities in feedback.entities_detected.items():
            if entity_type not in self.learned_patterns['entity_mappings']:
                self.learned_patterns['entity_mappings'][entity_type] = []
            
            if isinstance(entities, list):
                for entity in entities:
                    if entity not in self.learned_patterns['entity_mappings'][entity_type]:
                        self.learned_patterns['entity_mappings'][entity_type].append(entity)
    
    def _learn_error_pattern(self, feedback: QueryFeedback):
        """Learn from failed query"""
        error_pattern = {
            'question_pattern': self._extract_question_pattern(feedback.question),
            'entities': list(feedback.entities_detected.keys()),
            'error': feedback.error_message,
            'sql_attempted': feedback.sql_generated[:200] if feedback.sql_generated else None
        }
        
        self.learned_patterns['error_patterns'].append(error_pattern)
    
    def _learn_from_correction(self, feedback: QueryFeedback):
        """Learn from user corrections"""
        # Extract what was wrong and what was right
        correction_pattern = {
            'original_question': feedback.question,
            'wrong_sql': feedback.sql_generated,
            'correct_sql': feedback.correction,
            'entities': feedback.entities_detected,
            'classification': feedback.classification
        }
        
        # Store correction for future reference
        if 'corrections' not in self.learned_patterns:
            self.learned_patterns['corrections'] = []
        
        self.learned_patterns['corrections'].append(correction_pattern)
    
    def _extract_sql_pattern(self, sql: str) -> str:
        """Extract pattern from SQL query"""
        if not sql:
            return ""
        
        # Simple pattern extraction (can be enhanced)
        sql_lower = sql.lower()
        
        if 'firebase_query:' in sql_lower:
            return 'firebase_query'
        elif 'select' in sql_lower and 'join' in sql_lower:
            return 'select_with_join'
        elif 'select' in sql_lower and 'group by' in sql_lower:
            return 'select_with_groupby'
        elif 'select' in sql_lower:
            return 'simple_select'
        else:
            return 'other'
    
    def _extract_question_pattern(self, question: str) -> str:
        """Extract pattern from question"""
        question_lower = question.lower()
        
        # Common patterns
        patterns = {
            'count': ['how many', 'count', 'total number'],
            'list': ['list', 'show all', 'display'],
            'filter': ['where', 'filter', 'only'],
            'aggregate': ['average', 'sum', 'max', 'min'],
            'join': ['which', 'who', 'cross-reference']
        }
        
        for pattern_type, keywords in patterns.items():
            if any(keyword in question_lower for keyword in keywords):
                return pattern_type
        
        return 'other'
    
    def get_similar_successful_queries(self, question: str, 
                                      entities: Dict, 
                                      limit: int = 3) -> List[Dict]:
        """Find similar successful queries"""
        similar = []
        
        # Simple similarity based on entities
        question_entities = set(entities.keys())
        
        for feedback in self.recent_feedback:
            if feedback.user_feedback == 'positive':
                feedback_entities = set(feedback.entities_detected.keys())
                
                # Calculate similarity
                intersection = question_entities & feedback_entities
                union = question_entities | feedback_entities
                
                if union:
                    similarity = len(intersection) / len(union)
                    
                    if similarity > 0.5:
                        similar.append({
                            'question': feedback.question,
                            'sql': feedback.sql_generated,
                            'similarity': similarity,
                            'execution_time': feedback.execution_time
                        })
        
        # Sort by similarity
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similar[:limit]
    
    def get_recommendations(self, question: str, entities: Dict) -> Dict:
        """Get recommendations based on learned patterns"""
        recommendations = {
            'similar_queries': self.get_similar_successful_queries(question, entities),
            'avoid_patterns': [],
            'suggested_entities': [],
            'performance_hints': []
        }
        
        # Check for error patterns to avoid
        question_pattern = self._extract_question_pattern(question)
        for error in self.learned_patterns['error_patterns']:
            if error['question_pattern'] == question_pattern:
                recommendations['avoid_patterns'].append(error)
        
        # Suggest additional entities
        for entity_type in entities:
            if entity_type in self.learned_patterns['entity_mappings']:
                known_entities = self.learned_patterns['entity_mappings'][entity_type]
                recommendations['suggested_entities'].extend(known_entities[:3])
        
        # Performance hints
        if self.metrics['avg_execution_time'] > 0:
            recommendations['performance_hints'].append(
                f"Average query time: {self.metrics['avg_execution_time']:.2f}s"
            )
        
        return recommendations


class LearningEngine:
    """Automatic learning and improvement engine"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.improvement_suggestions = []
        self.retraining_queue = []
    
    def analyze_patterns(self) -> Dict:
        """Analyze feedback patterns for improvements"""
        analysis = {
            'common_errors': self._find_common_errors(),
            'successful_patterns': self._find_successful_patterns(),
            'improvement_areas': self._identify_improvement_areas(),
            'retraining_needed': False
        }
        
        # Check if retraining is needed
        metrics = self.feedback_collector.metrics
        if metrics['total_queries'] > 0:
            success_rate = metrics['successful_queries'] / metrics['total_queries']
            if success_rate < 0.8 and metrics['total_queries'] > 100:
                analysis['retraining_needed'] = True
        
        return analysis
    
    def _find_common_errors(self) -> List[Dict]:
        """Find common error patterns"""
        error_counts = Counter()
        
        for error in self.feedback_collector.learned_patterns['error_patterns']:
            if error['error']:
                # Simple error categorization
                if 'not found' in error['error'].lower():
                    error_counts['table_not_found'] += 1
                elif 'syntax' in error['error'].lower():
                    error_counts['syntax_error'] += 1
                elif 'firebase' in error['error'].lower():
                    error_counts['routing_error'] += 1
                else:
                    error_counts['other'] += 1
        
        return [
            {'type': error_type, 'count': count}
            for error_type, count in error_counts.most_common(5)
        ]
    
    def _find_successful_patterns(self) -> List[Dict]:
        """Find patterns in successful queries"""
        pattern_counts = Counter()
        
        for pattern in self.feedback_collector.learned_patterns['successful_patterns']:
            pattern_counts[pattern['sql_pattern']] += 1
        
        return [
            {'pattern': pattern, 'count': count}
            for pattern, count in pattern_counts.most_common(5)
        ]
    
    def _identify_improvement_areas(self) -> List[str]:
        """Identify areas needing improvement"""
        areas = []
        metrics = self.feedback_collector.metrics
        
        if metrics['total_queries'] > 0:
            # Check success rate
            success_rate = metrics['successful_queries'] / metrics['total_queries']
            if success_rate < 0.8:
                areas.append(f"Success rate low: {success_rate:.1%}")
            
            # Check correction rate
            if metrics['corrected_queries'] > metrics['total_queries'] * 0.1:
                areas.append(f"High correction rate: {metrics['corrected_queries']} corrections")
            
            # Check execution time
            if metrics['avg_execution_time'] > 5.0:
                areas.append(f"Slow queries: avg {metrics['avg_execution_time']:.1f}s")
        
        return areas
    
    def generate_training_data(self) -> List[Dict]:
        """Generate training data from feedback"""
        training_data = []
        
        # Use successful queries with positive feedback
        for feedback in self.feedback_collector.recent_feedback:
            if feedback.user_feedback == 'positive':
                training_data.append({
                    'input': feedback.question,
                    'output': feedback.sql_generated,
                    'entities': feedback.entities_detected,
                    'classification': feedback.classification,
                    'metadata': {
                        'execution_time': feedback.execution_time,
                        'row_count': feedback.row_count
                    }
                })
            elif feedback.correction:
                # Use corrections as training data
                training_data.append({
                    'input': feedback.question,
                    'output': feedback.correction,
                    'entities': feedback.entities_detected,
                    'classification': feedback.classification,
                    'metadata': {
                        'was_corrected': True,
                        'original_wrong': feedback.sql_generated
                    }
                })
        
        return training_data
    
    def should_retrain(self) -> bool:
        """Determine if model retraining is needed"""
        metrics = self.feedback_collector.metrics
        
        # Criteria for retraining
        if metrics['total_queries'] < 100:
            return False  # Not enough data
        
        success_rate = metrics['successful_queries'] / metrics['total_queries']
        
        # Retrain if success rate is low
        if success_rate < 0.75:
            return True
        
        # Retrain if many corrections
        correction_rate = metrics['corrected_queries'] / metrics['total_queries']
        if correction_rate > 0.15:
            return True
        
        return False
    
    def export_for_finetuning(self, output_file: str = "training_data.jsonl"):
        """Export training data for fine-tuning"""
        training_data = self.generate_training_data()
        
        with open(output_file, 'w') as f:
            for item in training_data:
                # Format for fine-tuning
                formatted = {
                    'prompt': item['input'],
                    'completion': item['output'],
                    'metadata': item.get('metadata', {})
                }
                f.write(json.dumps(formatted) + '\n')
        
        print(f"✅ Exported {len(training_data)} training examples to {output_file}")
        return len(training_data)


class PerformanceMonitor:
    """Monitor query performance and system health"""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.performance_log = []
    
    def get_current_stats(self) -> Dict:
        """Get current performance statistics"""
        metrics = self.feedback_collector.metrics
        
        if metrics['total_queries'] == 0:
            return {
                'status': 'No data',
                'total_queries': 0
            }
        
        success_rate = metrics['successful_queries'] / metrics['total_queries']
        
        return {
            'status': 'Healthy' if success_rate > 0.8 else 'Needs Attention',
            'total_queries': metrics['total_queries'],
            'success_rate': f"{success_rate:.1%}",
            'avg_execution_time': f"{metrics['avg_execution_time']:.2f}s",
            'failed_queries': metrics['failed_queries'],
            'corrections': metrics['corrected_queries'],
            'feedback_distribution': metrics['feedback_counts']
        }
    
    def get_trends(self, days: int = 7) -> Dict:
        """Get performance trends over time"""
        # Load recent feedback
        recent = []
        cutoff = datetime.now() - timedelta(days=days)
        
        if self.feedback_collector.feedback_file.exists():
            with open(self.feedback_collector.feedback_file, 'r') as f:
                for line in f:
                    feedback = json.loads(line)
                    timestamp = datetime.fromisoformat(feedback['timestamp'])
                    if timestamp > cutoff:
                        recent.append(feedback)
        
        # Calculate daily stats
        daily_stats = defaultdict(lambda: {
            'total': 0, 'successful': 0, 'failed': 0
        })
        
        for feedback in recent:
            date = feedback['timestamp'][:10]  # YYYY-MM-DD
            daily_stats[date]['total'] += 1
            
            if feedback['user_feedback'] == 'positive':
                daily_stats[date]['successful'] += 1
            elif feedback['error_message']:
                daily_stats[date]['failed'] += 1
        
        return dict(daily_stats)
    
    def generate_report(self) -> str:
        """Generate performance report"""
        stats = self.get_current_stats()
        trends = self.get_trends()
        analysis = LearningEngine(self.feedback_collector).analyze_patterns()
        
        report = f"""
📊 FF_Agent Performance Report
{'='*50}

📈 Current Statistics:
  Status: {stats.get('status', 'Unknown')}
  Total Queries: {stats.get('total_queries', 0)}
  Success Rate: {stats.get('success_rate', 'N/A')}
  Avg Execution Time: {stats.get('avg_execution_time', 'N/A')}
  Failed Queries: {stats.get('failed_queries', 0)}
  User Corrections: {stats.get('corrections', 0)}

📊 Feedback Distribution:
"""
        
        for feedback_type, count in stats.get('feedback_distribution', {}).items():
            report += f"  {feedback_type.capitalize()}: {count}\n"
        
        report += f"""
📉 Common Error Types:
"""
        for error in analysis['common_errors'][:3]:
            report += f"  - {error['type']}: {error['count']} occurrences\n"
        
        report += f"""
✅ Successful Query Patterns:
"""
        for pattern in analysis['successful_patterns'][:3]:
            report += f"  - {pattern['pattern']}: {pattern['count']} times\n"
        
        if analysis['improvement_areas']:
            report += f"""
⚠️  Areas Needing Attention:
"""
            for area in analysis['improvement_areas']:
                report += f"  - {area}\n"
        
        if analysis['retraining_needed']:
            report += """
🔄 Recommendation: Model retraining needed based on performance metrics
"""
        
        return report


# Testing function
def test_feedback_system():
    """Test the feedback system"""
    print("🧪 Testing Feedback System")
    print("="*60)
    
    # Create feedback collector
    collector = FeedbackCollector()
    
    # Simulate some feedback
    test_queries = [
        {
            'question': "List all staff",
            'sql': "FIREBASE_QUERY: staff",
            'entities': {'personnel': ['staff']},
            'classification': {'type': 'personnel', 'databases': ['firebase']},
            'execution_time': 0.5,
            'row_count': 10,
            'feedback': 'positive'
        },
        {
            'question': "Show drops in Lawley",
            'sql': "SELECT * FROM drops WHERE project='LAW'",
            'entities': {'project_codes': ['LAW']},
            'classification': {'type': 'infrastructure', 'databases': ['postgresql']},
            'execution_time': 1.2,
            'row_count': 100,
            'feedback': 'positive'
        },
        {
            'question': "Calculate PON utilization",
            'sql': "SELECT pon_id, COUNT(*) FROM drops",
            'entities': {'equipment': ['pon']},
            'classification': {'type': 'analytical', 'databases': ['postgresql']},
            'execution_time': 2.5,
            'row_count': 0,
            'feedback': 'negative',
            'error': "Missing GROUP BY",
            'correction': "SELECT pon_id, COUNT(*) FROM drops GROUP BY pon_id"
        }
    ]
    
    # Collect feedback
    for query in test_queries:
        feedback = collector.collect_feedback(
            question=query['question'],
            sql_generated=query['sql'],
            entities_detected=query['entities'],
            classification=query['classification'],
            execution_time=query['execution_time'],
            row_count=query['row_count'],
            user_feedback=query['feedback'],
            error_message=query.get('error'),
            correction=query.get('correction')
        )
        print(f"✅ Collected feedback for: {query['question']}")
    
    # Test learning engine
    print("\n🤖 Testing Learning Engine")
    engine = LearningEngine(collector)
    
    analysis = engine.analyze_patterns()
    print(f"  Common errors: {len(analysis['common_errors'])}")
    print(f"  Successful patterns: {len(analysis['successful_patterns'])}")
    print(f"  Improvement areas: {analysis['improvement_areas']}")
    
    # Test performance monitor
    print("\n📊 Testing Performance Monitor")
    monitor = PerformanceMonitor(collector)
    
    stats = monitor.get_current_stats()
    print(f"  Status: {stats['status']}")
    print(f"  Success rate: {stats['success_rate']}")
    
    # Generate report
    print("\n📋 Performance Report:")
    print(monitor.generate_report())
    
    # Export training data
    print("\n💾 Exporting Training Data")
    count = engine.export_for_finetuning("test_training_data.jsonl")
    print(f"  Exported {count} examples")
    
    return True


if __name__ == "__main__":
    test_feedback_system()