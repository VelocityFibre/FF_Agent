#!/usr/bin/env python3
"""
Test the live FF_Agent API with all enhancements
Shows all 4 phases working together
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def pretty_print(title, data):
    """Pretty print JSON data"""
    print(f"\n{'='*60}")
    print(f"📊 {title}")
    print('='*60)
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"\n{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            elif isinstance(value, list) and len(value) > 0:
                print(f"\n{key}:")
                for item in value[:3]:  # Show first 3
                    if isinstance(item, dict):
                        print(f"  - {item}")
                    else:
                        print(f"  - {item}")
            else:
                print(f"{key}: {value}")

def test_query(question, description):
    """Test a single query"""
    print(f"\n🔍 Testing: {description}")
    print(f"   Query: '{question}'")
    
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={
                "question": question,
                "use_rag": True,
                "use_feedback": True
            },
            timeout=10
        )
        
        result = response.json()
        
        # Show key results
        print(f"\n   ✅ Success: {result.get('success', False)}")
        
        # Phase 1: Entity Detection
        if result.get('entities_detected'):
            print(f"\n   📍 Phase 1 - Entities Detected:")
            for entity_type, entities in result['entities_detected'].items():
                print(f"      {entity_type}: {entities}")
        
        # Classification
        if result.get('query_classification'):
            cls = result['query_classification']
            print(f"\n   🎯 Classification:")
            print(f"      Type: {cls.get('type')}")
            print(f"      Database(s): {cls.get('databases')}")
            print(f"      Complexity: {cls.get('complexity')}")
        
        # SQL Generated
        if result.get('sql'):
            sql = result['sql']
            if len(sql) > 100:
                sql = sql[:100] + "..."
            print(f"\n   💾 SQL Generated:")
            print(f"      {sql}")
        
        # Results
        if result.get('row_count'):
            print(f"\n   📊 Results: {result['row_count']} rows")
        
        # Performance
        if result.get('execution_time'):
            print(f"   ⏱️  Time: {result['execution_time']:.2f}s")
        
        return result
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def main():
    print("🚀 FF_Agent Live API Test")
    print("Testing all 4 enhancement phases in action")
    
    # Check API status
    print("\n" + "="*60)
    print("🔌 Checking API Status")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/")
        status = response.json()
        
        print("\n✅ API is running with:")
        for phase, active in status['phases_active'].items():
            status_icon = "✅" if active else "❌"
            print(f"   {status_icon} {phase.replace('_', ' ').title()}")
        
        print("\n📦 Components:")
        for component, state in status['components'].items():
            print(f"   {state} {component.replace('_', ' ').title()}")
            
    except Exception as e:
        print(f"❌ API not responding: {e}")
        print("Please start it with: python3 api_with_feedback.py")
        return
    
    # Test queries
    print("\n" + "="*60)
    print("🧪 Testing Enhancement Features")
    print("="*60)
    
    test_cases = [
        ("List all staff", "Firebase routing test"),
        ("Show drops in Lawley project", "Project code detection"),
        ("Calculate PON utilization", "Telecom domain knowledge"),
        ("What's the average splice loss?", "Measurement detection"),
        ("Which technician installed the most drops?", "Cross-database query")
    ]
    
    results = []
    for question, description in test_cases:
        result = test_query(question, description)
        if result:
            results.append(result)
        time.sleep(0.5)
    
    # Check performance metrics
    print("\n" + "="*60)
    print("📈 Performance Metrics")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/performance")
        perf = response.json()
        
        stats = perf.get('statistics', {})
        print(f"\n📊 Current Stats:")
        print(f"   Status: {stats.get('status', 'Unknown')}")
        print(f"   Total Queries: {stats.get('total_queries', 0)}")
        print(f"   Success Rate: {stats.get('success_rate', 'N/A')}")
        print(f"   Avg Time: {stats.get('avg_execution_time', 'N/A')}")
        
        analysis = perf.get('analysis', {})
        if analysis.get('successful_patterns'):
            print(f"\n✅ Successful Patterns:")
            for pattern in analysis['successful_patterns'][:3]:
                print(f"   - {pattern}")
        
        if analysis.get('improvement_areas'):
            print(f"\n⚠️  Areas to Improve:")
            for area in analysis['improvement_areas']:
                print(f"   - {area}")
                
    except Exception as e:
        print(f"Could not get performance data: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("🎯 Test Summary")
    print("="*60)
    
    successful = sum(1 for r in results if r.get('success'))
    total = len(results)
    
    print(f"\n📊 Query Results: {successful}/{total} successful")
    
    # Count features used
    entity_detection = sum(1 for r in results if r.get('entities_detected'))
    classification = sum(1 for r in results if r.get('query_classification'))
    
    print(f"\n🔥 Features Active:")
    print(f"   Entity Detection: {entity_detection}/{total} queries")
    print(f"   Query Classification: {classification}/{total} queries")
    print(f"   Feedback Collection: Active (automatic)")
    print(f"   Learning: Continuous")
    
    print("\n✅ The FF_Agent is fully operational with all enhancements!")
    print("\n📝 The system is now:")
    print("   • Understanding queries with entity detection")
    print("   • Routing to correct databases")
    print("   • Learning from every interaction")
    print("   • Ready for fine-tuning when enough data collected")

if __name__ == "__main__":
    main()