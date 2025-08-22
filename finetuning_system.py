#!/usr/bin/env python3
"""
Fine-Tuning System for FF_Agent
Phase 4: Domain-Specific Model Training
Creates a FibreFlow-specialized model from collected feedback
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import hashlib
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict

@dataclass
class TrainingExample:
    """Structure for training examples"""
    id: str
    prompt: str
    completion: str
    metadata: Dict
    
    def to_openai_format(self) -> Dict:
        """Convert to OpenAI fine-tuning format"""
        return {
            "messages": [
                {"role": "system", "content": "You are a SQL expert for FibreFlow telecommunications database."},
                {"role": "user", "content": self.prompt},
                {"role": "assistant", "content": self.completion}
            ]
        }
    
    def to_gemini_format(self) -> Dict:
        """Convert to Gemini fine-tuning format"""
        return {
            "text_input": self.prompt,
            "output": self.completion
        }

class FineTuningDataPreparer:
    """Prepares data for fine-tuning from feedback system"""
    
    def __init__(self, feedback_path: str = "feedback_data"):
        self.feedback_path = Path(feedback_path)
        self.training_examples = []
        self.validation_examples = []
        self.test_examples = []
        
        # FibreFlow-specific patterns
        self.domain_patterns = {
            'project_prefixes': ['LAW', 'IVY', 'MAM', 'MOH', 'HEIN'],
            'telecom_terms': [
                'PON', 'OLT', 'ONU', 'splice loss', 'optical power',
                'attenuation', 'drop', 'pole', 'fibre'
            ],
            'calculations': {
                'pon_utilization': '(COUNT(*) * 100.0 / 32)',
                'take_rate': '(active_drops * 100.0 / homes_passed)',
                'avg_splice_loss': 'AVG(splice_loss_db)'
            }
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'min_execution_time': 0.1,
            'max_execution_time': 10.0,
            'min_row_count': 0,
            'max_row_count': 10000
        }
    
    def load_feedback_data(self) -> List[Dict]:
        """Load feedback data from disk"""
        feedback_file = self.feedback_path / "feedback_log.jsonl"
        data = []
        
        if feedback_file.exists():
            with open(feedback_file, 'r') as f:
                for line in f:
                    try:
                        data.append(json.loads(line))
                    except:
                        continue
        
        return data
    
    def load_corrections(self) -> List[Dict]:
        """Load user corrections"""
        patterns_file = self.feedback_path / "learned_patterns.json"
        
        if patterns_file.exists():
            with open(patterns_file, 'r') as f:
                patterns = json.load(f)
                return patterns.get('corrections', [])
        
        return []
    
    def prepare_training_data(self, min_examples: int = 100) -> Tuple[int, int, int]:
        """
        Prepare training data from feedback
        
        Returns:
            Tuple of (train_count, val_count, test_count)
        """
        # Load all data
        feedback_data = self.load_feedback_data()
        corrections = self.load_corrections()
        
        print(f"📊 Loaded {len(feedback_data)} feedback entries")
        print(f"📝 Loaded {len(corrections)} corrections")
        
        # Process feedback into training examples
        examples = []
        
        # Add successful queries
        for item in feedback_data:
            if item.get('user_feedback') == 'positive':
                example = self._create_training_example(item)
                if example and self._validate_example(example):
                    examples.append(example)
        
        # Add corrections with higher weight
        for correction in corrections:
            example = self._create_correction_example(correction)
            if example and self._validate_example(example):
                # Add corrections multiple times for emphasis
                examples.extend([example] * 2)
        
        # Add synthetic examples for domain knowledge
        synthetic = self._generate_synthetic_examples()
        examples.extend(synthetic)
        
        print(f"✅ Created {len(examples)} training examples")
        
        if len(examples) < min_examples:
            print(f"⚠️  Not enough examples. Need at least {min_examples}, have {len(examples)}")
            
            # Generate more synthetic examples
            additional_needed = min_examples - len(examples)
            print(f"🔧 Generating {additional_needed} additional synthetic examples...")
            examples.extend(self._generate_synthetic_examples(count=additional_needed))
        
        # Shuffle and split
        random.shuffle(examples)
        
        # 70% train, 15% validation, 15% test
        train_size = int(len(examples) * 0.7)
        val_size = int(len(examples) * 0.15)
        
        self.training_examples = examples[:train_size]
        self.validation_examples = examples[train_size:train_size+val_size]
        self.test_examples = examples[train_size+val_size:]
        
        return len(self.training_examples), len(self.validation_examples), len(self.test_examples)
    
    def _create_training_example(self, feedback: Dict) -> Optional[TrainingExample]:
        """Create training example from feedback"""
        try:
            return TrainingExample(
                id=feedback.get('query_id', hashlib.md5(str(feedback).encode()).hexdigest()[:8]),
                prompt=self._enhance_prompt(feedback['question']),
                completion=self._enhance_completion(feedback['sql_generated']),
                metadata={
                    'source': 'feedback',
                    'execution_time': feedback.get('execution_time', 0),
                    'row_count': feedback.get('row_count', 0),
                    'entities': feedback.get('entities_detected', {}),
                    'classification': feedback.get('classification', {})
                }
            )
        except:
            return None
    
    def _create_correction_example(self, correction: Dict) -> Optional[TrainingExample]:
        """Create training example from correction"""
        try:
            return TrainingExample(
                id=hashlib.md5(str(correction).encode()).hexdigest()[:8],
                prompt=self._enhance_prompt(correction['original_question']),
                completion=self._enhance_completion(correction['correct_sql']),
                metadata={
                    'source': 'correction',
                    'was_wrong': correction.get('wrong_sql', ''),
                    'entities': correction.get('entities', {}),
                    'classification': correction.get('classification', {})
                }
            )
        except:
            return None
    
    def _enhance_prompt(self, question: str) -> str:
        """Enhance prompt with context"""
        enhanced = f"Question: {question}\n"
        enhanced += "Context: You have access to FibreFlow database with tables:\n"
        enhanced += "- PostgreSQL: projects, sow_drops, sow_poles, nokia_data\n"
        enhanced += "- Firebase: staff, users\n"
        enhanced += "Generate SQL query:"
        return enhanced
    
    def _enhance_completion(self, sql: str) -> str:
        """Enhance SQL with comments"""
        if "FIREBASE_QUERY:" in sql:
            return sql
        
        # Add helpful comments
        enhanced = sql
        
        # Add calculation explanations
        if "COUNT(*) * 100.0 / 32" in sql:
            enhanced = "-- PON utilization: 32 ports per PON\n" + enhanced
        if "AVG(" in sql and "splice" in sql.lower():
            enhanced = "-- Splice loss in dB, acceptable range 0.1-0.5\n" + enhanced
        
        return enhanced
    
    def _validate_example(self, example: TrainingExample) -> bool:
        """Validate training example quality"""
        # Check prompt length
        if len(example.prompt) < 10 or len(example.prompt) > 500:
            return False
        
        # Check completion length
        if len(example.completion) < 10 or len(example.completion) > 1000:
            return False
        
        # Check execution time if available
        exec_time = example.metadata.get('execution_time', 1)
        if exec_time < self.quality_thresholds['min_execution_time']:
            return False
        if exec_time > self.quality_thresholds['max_execution_time']:
            return False
        
        return True
    
    def _generate_synthetic_examples(self, count: int = 50) -> List[TrainingExample]:
        """Generate synthetic training examples for domain knowledge"""
        examples = []
        
        # Templates for different query types
        templates = [
            # Project queries
            {
                'question': "Show all drops in {project} project",
                'sql': "SELECT * FROM sow_drops WHERE drop_number LIKE '{prefix}%' LIMIT 100;",
                'vars': {'project': 'Lawley', 'prefix': 'LAW'}
            },
            {
                'question': "Count drops in {project}",
                'sql': "SELECT COUNT(*) as total FROM sow_drops WHERE drop_number LIKE '{prefix}%';",
                'vars': {'project': 'Ivory Park', 'prefix': 'IVY'}
            },
            
            # PON queries
            {
                'question': "Calculate PON utilization",
                'sql': """SELECT 
                    pon_id,
                    COUNT(*) as connected_drops,
                    (COUNT(*) * 100.0 / 32) as utilization_percentage
                FROM sow_drops
                WHERE pon_id IS NOT NULL
                GROUP BY pon_id
                ORDER BY utilization_percentage DESC;""",
                'vars': {}
            },
            
            # Splice loss queries
            {
                'question': "What's the average splice loss in {project}?",
                'sql': """SELECT 
                    AVG(splice_loss_db) as avg_loss,
                    MIN(splice_loss_db) as min_loss,
                    MAX(splice_loss_db) as max_loss
                FROM sow_drops
                WHERE drop_number LIKE '{prefix}%'
                    AND splice_loss_db IS NOT NULL;""",
                'vars': {'project': 'Mamelodi', 'prefix': 'MAM'}
            },
            
            # Staff queries
            {
                'question': "List all staff members",
                'sql': "FIREBASE_QUERY: staff",
                'vars': {}
            },
            {
                'question': "Show all employees",
                'sql': "FIREBASE_QUERY: staff",
                'vars': {}
            },
            {
                'question': "Get field technicians",
                'sql': "FIREBASE_QUERY: staff WHERE role='field_technician'",
                'vars': {}
            },
            
            # Complex queries
            {
                'question': "Which pole has the most drops?",
                'sql': """SELECT 
                    pole_number,
                    COUNT(*) as drop_count
                FROM sow_drops
                WHERE pole_number IS NOT NULL
                GROUP BY pole_number
                ORDER BY drop_count DESC
                LIMIT 1;""",
                'vars': {}
            },
            
            # Status queries
            {
                'question': "Show inactive drops in {project}",
                'sql': """SELECT 
                    drop_number,
                    status,
                    last_updated
                FROM sow_drops
                WHERE drop_number LIKE '{prefix}%'
                    AND status = 'inactive'
                ORDER BY last_updated DESC
                LIMIT 100;""",
                'vars': {'project': 'Mohadin', 'prefix': 'MOH'}
            }
        ]
        
        # Generate variations
        projects = [
            {'name': 'Lawley', 'prefix': 'LAW'},
            {'name': 'Ivory Park', 'prefix': 'IVY'},
            {'name': 'Mamelodi', 'prefix': 'MAM'},
            {'name': 'Mohadin', 'prefix': 'MOH'}
        ]
        
        for i in range(min(count, len(templates) * len(projects))):
            template = templates[i % len(templates)]
            
            # Create variation
            if template['vars']:
                if 'project' in template['vars']:
                    project = projects[i % len(projects)]
                    question = template['question'].format(project=project['name'])
                    sql = template['sql'].format(prefix=project['prefix'])
                else:
                    question = template['question'].format(**template['vars'])
                    sql = template['sql'].format(**template['vars'])
            else:
                question = template['question']
                sql = template['sql']
            
            example = TrainingExample(
                id=f"synthetic_{i}",
                prompt=self._enhance_prompt(question),
                completion=sql,
                metadata={
                    'source': 'synthetic',
                    'template_id': i % len(templates)
                }
            )
            
            examples.append(example)
        
        return examples[:count]
    
    def export_for_training(self, format: str = 'openai') -> Dict[str, str]:
        """
        Export prepared data for fine-tuning
        
        Args:
            format: 'openai' or 'gemini'
        
        Returns:
            Dict with file paths
        """
        output_dir = Path("finetuning_data")
        output_dir.mkdir(exist_ok=True)
        
        files = {}
        
        # Export training set
        train_file = output_dir / f"train_{format}.jsonl"
        with open(train_file, 'w') as f:
            for example in self.training_examples:
                if format == 'openai':
                    f.write(json.dumps(example.to_openai_format()) + '\n')
                else:
                    f.write(json.dumps(example.to_gemini_format()) + '\n')
        files['train'] = str(train_file)
        
        # Export validation set
        val_file = output_dir / f"validation_{format}.jsonl"
        with open(val_file, 'w') as f:
            for example in self.validation_examples:
                if format == 'openai':
                    f.write(json.dumps(example.to_openai_format()) + '\n')
                else:
                    f.write(json.dumps(example.to_gemini_format()) + '\n')
        files['validation'] = str(val_file)
        
        # Export test set
        test_file = output_dir / f"test_{format}.jsonl"
        with open(test_file, 'w') as f:
            for example in self.test_examples:
                if format == 'openai':
                    f.write(json.dumps(example.to_openai_format()) + '\n')
                else:
                    f.write(json.dumps(example.to_gemini_format()) + '\n')
        files['test'] = str(test_file)
        
        print(f"✅ Exported {format} format files:")
        for split, path in files.items():
            print(f"  {split}: {path}")
        
        return files
    
    def analyze_dataset(self) -> Dict:
        """Analyze the prepared dataset"""
        all_examples = self.training_examples + self.validation_examples + self.test_examples
        
        analysis = {
            'total_examples': len(all_examples),
            'splits': {
                'train': len(self.training_examples),
                'validation': len(self.validation_examples),
                'test': len(self.test_examples)
            },
            'sources': Counter(),
            'query_types': Counter(),
            'databases': Counter(),
            'avg_prompt_length': 0,
            'avg_completion_length': 0
        }
        
        prompt_lengths = []
        completion_lengths = []
        
        for example in all_examples:
            # Count sources
            source = example.metadata.get('source', 'unknown')
            analysis['sources'][source] += 1
            
            # Analyze queries
            if 'FIREBASE_QUERY' in example.completion:
                analysis['databases']['firebase'] += 1
            else:
                analysis['databases']['postgresql'] += 1
            
            # Analyze query types
            completion_lower = example.completion.lower()
            if 'select' in completion_lower:
                if 'group by' in completion_lower:
                    analysis['query_types']['aggregate'] += 1
                elif 'join' in completion_lower:
                    analysis['query_types']['join'] += 1
                else:
                    analysis['query_types']['simple_select'] += 1
            
            # Track lengths
            prompt_lengths.append(len(example.prompt))
            completion_lengths.append(len(example.completion))
        
        analysis['avg_prompt_length'] = sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0
        analysis['avg_completion_length'] = sum(completion_lengths) / len(completion_lengths) if completion_lengths else 0
        
        return analysis


class ModelTrainer:
    """Handles model fine-tuning orchestration"""
    
    def __init__(self):
        self.training_config = {
            'model': 'gemini-1.5-flash',  # or 'gpt-3.5-turbo'
            'epochs': 3,
            'batch_size': 4,
            'learning_rate': 2e-5,
            'warmup_steps': 100
        }
        
        self.training_history = []
    
    def validate_data(self, data_files: Dict[str, str]) -> bool:
        """Validate training data format"""
        try:
            # Check train file
            with open(data_files['train'], 'r') as f:
                for i, line in enumerate(f):
                    if i >= 5:  # Check first 5 lines
                        break
                    json.loads(line)
            
            print("✅ Training data validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Data validation failed: {e}")
            return False
    
    def estimate_training_cost(self, data_files: Dict[str, str]) -> Dict:
        """Estimate training cost"""
        # Count tokens (simplified)
        total_tokens = 0
        
        with open(data_files['train'], 'r') as f:
            for line in f:
                data = json.loads(line)
                # Rough estimate: 1 token per 4 characters
                if 'messages' in data:  # OpenAI format
                    for msg in data['messages']:
                        total_tokens += len(msg['content']) / 4
                else:  # Gemini format
                    total_tokens += (len(data.get('text_input', '')) + 
                                   len(data.get('output', ''))) / 4
        
        # Cost estimates (example rates)
        cost_per_1k_tokens = 0.008  # Example rate
        estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens * self.training_config['epochs']
        
        return {
            'total_tokens': int(total_tokens),
            'epochs': self.training_config['epochs'],
            'estimated_cost_usd': round(estimated_cost, 2),
            'estimated_time_hours': round(total_tokens / 100000, 1)  # Rough estimate
        }
    
    def create_training_script(self) -> str:
        """Create training script for the model"""
        script = '''#!/bin/bash
# Fine-tuning script for FF_Agent

echo "🚀 Starting Fine-tuning Process"
echo "================================"

# For OpenAI GPT
# openai api fine_tunes.create \\
#   -t finetuning_data/train_openai.jsonl \\
#   -v finetuning_data/validation_openai.jsonl \\
#   --model gpt-3.5-turbo \\
#   --n_epochs 3

# For Google Gemini (using Vertex AI)
# gcloud ai custom-jobs create \\
#   --region=us-central1 \\
#   --display-name="ff-agent-finetuning" \\
#   --config=training_config.yaml

echo "✅ Fine-tuning job submitted"
echo "Monitor progress in your cloud console"
'''
        
        with open('finetune.sh', 'w') as f:
            f.write(script)
        
        os.chmod('finetune.sh', 0o755)
        print("✅ Created finetune.sh script")
        
        return script


class ModelEvaluator:
    """Evaluate fine-tuned model performance"""
    
    def __init__(self):
        self.metrics = {
            'accuracy': 0,
            'execution_success_rate': 0,
            'avg_response_time': 0,
            'error_rate': 0
        }
    
    def evaluate_model(self, test_file: str, model_name: str = None) -> Dict:
        """Evaluate model on test set"""
        print(f"📊 Evaluating model on test set...")
        
        # Load test data
        test_examples = []
        with open(test_file, 'r') as f:
            for line in f:
                test_examples.append(json.loads(line))
        
        print(f"  Testing on {len(test_examples)} examples")
        
        # Simulate evaluation (in production, would call actual model)
        results = {
            'total_tests': len(test_examples),
            'successful': 0,
            'failed': 0,
            'improvements': [],
            'regressions': []
        }
        
        for example in test_examples[:10]:  # Test first 10
            # Simulate test
            success = random.random() > 0.2  # 80% success rate simulation
            
            if success:
                results['successful'] += 1
            else:
                results['failed'] += 1
        
        results['success_rate'] = results['successful'] / max(1, results['successful'] + results['failed'])
        
        # Compare with baseline
        baseline_success_rate = 0.7  # Previous success rate
        if results['success_rate'] > baseline_success_rate:
            results['improvement'] = f"+{(results['success_rate'] - baseline_success_rate)*100:.1f}%"
        else:
            results['improvement'] = f"{(results['success_rate'] - baseline_success_rate)*100:.1f}%"
        
        return results
    
    def generate_evaluation_report(self, results: Dict) -> str:
        """Generate evaluation report"""
        report = f"""
📊 Fine-Tuned Model Evaluation Report
=====================================

Test Set Size: {results['total_tests']} examples
Successful: {results['successful']}
Failed: {results['failed']}

Success Rate: {results['success_rate']:.1%}
Improvement: {results.get('improvement', 'N/A')}

Recommendation: {"Deploy" if results['success_rate'] > 0.75 else "Continue Training"}
"""
        return report


def test_finetuning_system():
    """Test the complete fine-tuning system"""
    print("🎯 Testing Fine-Tuning System (Phase 4)")
    print("="*60)
    
    # Initialize components
    preparer = FineTuningDataPreparer()
    trainer = ModelTrainer()
    evaluator = ModelEvaluator()
    
    # Prepare data
    print("\n1️⃣ Preparing Training Data")
    train_count, val_count, test_count = preparer.prepare_training_data(min_examples=50)
    print(f"  Train: {train_count}, Validation: {val_count}, Test: {test_count}")
    
    # Analyze dataset
    print("\n2️⃣ Analyzing Dataset")
    analysis = preparer.analyze_dataset()
    print(f"  Total examples: {analysis['total_examples']}")
    print(f"  Sources: {dict(analysis['sources'])}")
    print(f"  Query types: {dict(analysis['query_types'])}")
    
    # Export data
    print("\n3️⃣ Exporting Training Data")
    files = preparer.export_for_training(format='openai')
    
    # Validate data
    print("\n4️⃣ Validating Data Format")
    trainer.validate_data(files)
    
    # Estimate cost
    print("\n5️⃣ Estimating Training Cost")
    cost_estimate = trainer.estimate_training_cost(files)
    print(f"  Total tokens: {cost_estimate['total_tokens']:,}")
    print(f"  Estimated cost: ${cost_estimate['estimated_cost_usd']}")
    print(f"  Estimated time: {cost_estimate['estimated_time_hours']} hours")
    
    # Create training script
    print("\n6️⃣ Creating Training Script")
    trainer.create_training_script()
    
    # Simulate evaluation
    print("\n7️⃣ Simulating Model Evaluation")
    eval_results = evaluator.evaluate_model(files['test'])
    report = evaluator.generate_evaluation_report(eval_results)
    print(report)
    
    print("="*60)
    print("✅ Fine-Tuning System Test Complete!")
    
    return True


if __name__ == "__main__":
    test_finetuning_system()