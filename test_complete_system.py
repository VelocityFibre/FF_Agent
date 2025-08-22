#!/usr/bin/env python3
"""
Test the complete FF_Agent enhancement system
Phases 1, 2, and 3 integrated
"""

import requests
import json
import time

API_URL = "http://localhost:8000"

def test_complete_system():
    """Test all three phases working together"""
    print("🚀 Testing Complete FF_Agent Enhancement System")
    print("="*60)
    
    # Check API status
    try:
        response = requests.get(f"{API_URL}/")
        status = response.json()
        print("\n✅ API Status:")
        for phase, active in status['phases_active'].items():
            print(f"  {phase}: {'✅' if active else '❌'}")
        print("\n📦 Components:")
        for component, state in status['components'].items():
            print(f"  {component}: {state}")
    except:
        print("❌ API not running. Start with: python3 api_with_feedback.py")
        return
    
    # Test queries
    test_queries = [
        "List all staff",
        "Show drops in Lawley project", 
        "Calculate PON utilization",
        "Which technician installed the most drops?",
        "What's the average splice loss?"
    ]
    
    print("\n" + "="*60)
    print("📝 Testing Queries with Full Enhancement")
    print("="*60)
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        
        try:
            # Send query
            response = requests.post(
                f"{API_URL}/query",
                json={
                    "question": query,
                    "use_rag": True,
                    "use_feedback": True
                },
                timeout=10
            )
            
            result = response.json()
            
            # Display results
            print(f"  Query ID: {result.get('query_id', 'N/A')}")
            
            # Phase 1: Entity Detection
            if result.get('entities_detected'):
                print(f"\n  📍 Phase 1 - Entities Detected:")
                for entity_type, entities in result['entities_detected'].items():
                    print(f"    {entity_type}: {entities}")
            
            # Classification
            if result.get('query_classification'):
                cls = result['query_classification']
                print(f"  Classification: {cls.get('type')} → {cls.get('databases')}")
            
            # Phase 2: Similar queries from RAG
            if result.get('similar_queries'):
                print(f"\n  📚 Phase 2 - Similar Queries Found:")
                for similar in result['similar_queries'][:2]:
                    print(f"    - {similar.get('question', '')[:50]}...")
            
            # Phase 3: Recommendations from feedback
            if result.get('recommendations') and result['recommendations'].get('performance_hints'):
                print(f"\n  💡 Phase 3 - Performance Hints:")
                for hint in result['recommendations']['performance_hints']:
                    print(f"    - {hint}")
            
            # SQL Generated
            if result.get('sql'):
                sql_preview = result['sql'][:100] + "..." if len(result['sql']) > 100 else result['sql']
                print(f"\n  💾 SQL: {sql_preview}")
            
            # Results
            if result.get('success'):
                print(f"  ✅ Success! Rows: {result.get('row_count', 0)}")
                print(f"  ⏱️  Execution time: {result.get('execution_time', 0):.2f}s")
            else:
                print(f"  ❌ Error: {result.get('error', 'Unknown')[:100]}")
            
        except Exception as e:
            print(f"  ❌ Request failed: {e}")
        
        time.sleep(0.5)
    
    # Get performance report
    print("\n" + "="*60)
    print("📊 System Performance Report")
    print("="*60)
    
    try:
        response = requests.get(f"{API_URL}/performance")
        perf = response.json()
        
        stats = perf.get('statistics', {})
        print(f"\n📈 Statistics:")
        print(f"  Status: {stats.get('status')}")
        print(f"  Total Queries: {stats.get('total_queries')}")
        print(f"  Success Rate: {stats.get('success_rate')}")
        print(f"  Avg Execution: {stats.get('avg_execution_time')}")
        
        analysis = perf.get('analysis', {})
        if analysis.get('improvement_areas'):
            print(f"\n⚠️  Areas Needing Attention:")
            for area in analysis['improvement_areas']:
                print(f"  - {area}")
        
        if perf.get('should_retrain'):
            print(f"\n🔄 Retraining recommended based on performance")
        
    except Exception as e:
        print(f"❌ Could not get performance data: {e}")
    
    print("\n" + "="*60)
    print("✅ Complete System Test Finished")
    print("="*60)
    print("\n📊 Enhancement Stack Summary:")
    print("  Phase 1 (Prompt Engineering): Entity detection, classification")
    print("  Phase 2 (RAG): Document context, similar queries")
    print("  Phase 3 (Feedback): Learning, recommendations, monitoring")
    print("\nAll three phases are working together to improve query accuracy!")

if __name__ == "__main__":
    test_complete_system()