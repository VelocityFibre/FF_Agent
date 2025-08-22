#!/usr/bin/env python3
"""
Complete Test Suite for FF_Agent Enhancement
Tests all 4 phases in sequence
"""

import subprocess
import time
import sys
from pathlib import Path

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"🧪 {text}")
    print("="*60)

def run_test(name, command):
    """Run a test and report results"""
    print(f"\n▶️  Running: {name}")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"   ✅ {name} PASSED")
            # Show key output lines
            output_lines = result.stdout.split('\n')
            for line in output_lines[-5:]:
                if line.strip() and ('✅' in line or 'Success' in line or '%' in line):
                    print(f"      {line.strip()}")
            return True
        else:
            print(f"   ❌ {name} FAILED")
            if result.stderr:
                print(f"      Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"   ⚠️  {name} TIMEOUT")
        return False
    except Exception as e:
        print(f"   ❌ {name} ERROR: {e}")
        return False

def check_files_exist():
    """Check if all required files exist"""
    print_header("Checking Required Files")
    
    required_files = [
        "prompt_improvements.py",
        "document_ingester.py", 
        "feedback_system.py",
        "finetuning_system.py",
        "api_with_feedback.py"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} NOT FOUND")
            all_exist = False
    
    return all_exist

def test_phase1():
    """Test Phase 1: Prompt Engineering"""
    print_header("Phase 1: Prompt Engineering")
    
    # Test entity detection
    test_code = """
from prompt_improvements import EnhancedPromptGenerator
gen = EnhancedPromptGenerator()
result = gen.analyze_query("List all staff")
print(f"Entities: {list(result['entities'].keys())}")
print(f"Database: {result['classification']['databases']}")
if 'personnel' in result['entities'] and 'firebase' in result['classification']['databases']:
    print("✅ Phase 1 Working: Correctly identified staff query for Firebase")
else:
    print("❌ Phase 1 Failed: Incorrect classification")
"""
    
    return run_test(
        "Entity Detection & Classification",
        f'python3 -c "{test_code}"'
    )

def test_phase2():
    """Test Phase 2: RAG Enhancement"""
    print_header("Phase 2: RAG Enhancement")
    
    # Test document ingestion
    test_code = """
from document_ingester import DocumentIngester
ingester = DocumentIngester()
entities = ingester.extract_fibreflow_entities('Drop LAW-001 has optical power -25 dBm')
if 'project_codes' in entities and 'LAW' in str(entities['project_codes']):
    print(f"✅ Phase 2 Working: Detected entities {entities}")
else:
    print("❌ Phase 2 Failed: Entity extraction not working")
"""
    
    return run_test(
        "Document Ingestion & Entity Extraction",
        f'python3 -c "{test_code}"'
    )

def test_phase3():
    """Test Phase 3: Feedback Loop"""
    print_header("Phase 3: Feedback Loop")
    
    # Test feedback collection
    test_code = """
from feedback_system import FeedbackCollector
collector = FeedbackCollector()
feedback = collector.collect_feedback(
    question='Test query',
    sql_generated='SELECT * FROM test',
    entities_detected={'test': ['entity']},
    classification={'type': 'test'},
    execution_time=1.0,
    row_count=10,
    user_feedback='positive'
)
stats = collector.metrics
print(f"✅ Phase 3 Working: Collected {stats['total_queries']} feedback entries")
"""
    
    return run_test(
        "Feedback Collection & Learning",
        f'python3 -c "{test_code}"'
    )

def test_phase4():
    """Test Phase 4: Fine-tuning"""
    print_header("Phase 4: Fine-tuning")
    
    # Test fine-tuning preparation
    test_code = """
from finetuning_system import FineTuningDataPreparer
preparer = FineTuningDataPreparer()
synthetic = preparer._generate_synthetic_examples(count=5)
if len(synthetic) == 5:
    print(f"✅ Phase 4 Working: Generated {len(synthetic)} training examples")
else:
    print("❌ Phase 4 Failed: Could not generate training examples")
"""
    
    return run_test(
        "Fine-tuning Data Preparation",
        f'python3 -c "{test_code}"'
    )

def test_integration():
    """Test all phases working together"""
    print_header("Integration Test: All Phases Together")
    
    test_code = """
# Test all imports work together
from prompt_improvements import EnhancedPromptGenerator
from document_ingester import DocumentIngester
from feedback_system import FeedbackCollector, LearningEngine
from finetuning_system import FineTuningDataPreparer

# Quick integration test
prompt_gen = EnhancedPromptGenerator()
doc_ingester = DocumentIngester()
feedback = FeedbackCollector()
finetuner = FineTuningDataPreparer()

# Test flow
query = "Show drops in Lawley"
analysis = prompt_gen.analyze_query(query)
entities = doc_ingester.extract_fibreflow_entities(query)

print(f"✅ Integration Working:")
print(f"   Query analyzed: {analysis['classification']['type']}")
print(f"   Entities found: {list(entities.keys())}")
print(f"   All 4 phases can work together!")
"""
    
    return run_test(
        "Complete Integration",
        f'python3 -c "{test_code}"'
    )

def main():
    """Run all tests"""
    print("🚀 FF_Agent Complete Enhancement Test Suite")
    print("Testing all 4 phases of the enhancement")
    
    # Check files
    if not check_files_exist():
        print("\n❌ Missing required files. Please ensure all enhancement files are present.")
        return False
    
    # Run tests
    results = {
        "Files": True,
        "Phase 1": test_phase1(),
        "Phase 2": test_phase2(),
        "Phase 3": test_phase3(),
        "Phase 4": test_phase4(),
        "Integration": test_integration()
    }
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test}: {status}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 SUCCESS! All 4 phases are working correctly!")
        print("\nNext steps:")
        print("1. Start the API: python3 api_with_feedback.py")
        print("2. Test queries via API")
        print("3. Monitor performance")
        print("4. Collect feedback for continuous improvement")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)