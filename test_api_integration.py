#!/usr/bin/env python3
"""
Test script for the integrated API with prompt improvements
Tests entity detection, routing, and SQL generation through the API
"""

import requests
import json
from typing import Dict, List
import time

# API configuration
API_URL = "http://localhost:8000"

def test_query(question: str, use_vector: bool = True) -> Dict:
    """Send a query to the API and return the response"""
    
    try:
        response = requests.post(
            f"{API_URL}/query",
            json={
                "question": question,
                "use_vector_search": use_vector
            },
            timeout=10
        )
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "API not running. Start with: python3 api_enhanced.py"}
    except Exception as e:
        return {"error": str(e)}

def print_result(query: str, result: Dict):
    """Pretty print query results"""
    
    print(f"\n{'='*70}")
    print(f"📝 Query: {query}")
    print(f"{'='*70}")
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    # Show classification and entities
    if result.get('query_classification'):
        classification = result['query_classification']
        print(f"\n🎯 Classification:")
        print(f"   Type: {classification.get('type', 'unknown')}")
        print(f"   Complexity: {classification.get('complexity', 'unknown')}")
        print(f"   Database(s): {', '.join(classification.get('databases', []))}")
        if classification.get('needs_join'):
            print(f"   ⚠️  Needs cross-database join")
    
    if result.get('entities_detected'):
        entities = result['entities_detected']
        if entities:
            print(f"\n🔍 Entities Detected:")
            for category, items in entities.items():
                if isinstance(items, list):
                    print(f"   {category}: {', '.join(items)}")
                else:
                    print(f"   {category}: {items}")
    
    # Show SQL
    if result.get('sql'):
        print(f"\n💾 Generated SQL:")
        sql_preview = result['sql'][:200] + "..." if len(result['sql']) > 200 else result['sql']
        print(f"   {sql_preview}")
    
    # Show results
    if result.get('success'):
        print(f"\n✅ Success!")
        print(f"   Rows returned: {result.get('row_count', 0)}")
        if result.get('vector_context_used'):
            print(f"   Vector search used: Yes")
            print(f"   Similar queries found: {result.get('similar_queries_found', 0)}")
        
        # Show sample data
        if result.get('data') and len(result['data']) > 0:
            print(f"\n📊 Sample Data (first 3 rows):")
            for i, row in enumerate(result['data'][:3], 1):
                print(f"   Row {i}: {json.dumps(row, default=str)[:100]}...")
    else:
        print(f"\n❌ Query Failed")
        if result.get('error'):
            print(f"   Error: {result['error'][:200]}")

def run_test_suite():
    """Run comprehensive test suite"""
    
    print("🚀 TESTING INTEGRATED API WITH PROMPT IMPROVEMENTS")
    print("="*70)
    
    # Test queries covering different scenarios
    test_queries = [
        # PostgreSQL queries
        ("How many drops are in the system?", "Should detect 'drops' entity and route to PostgreSQL"),
        ("Show all projects with their creation dates", "Should detect 'projects' and use PostgreSQL"),
        ("List poles in Lawley", "Should detect 'Lawley' project code and 'poles'"),
        
        # Firebase queries
        ("List all staff", "Should detect 'staff' and route to Firebase"),
        ("Show all employees", "Should detect 'employees' and route to Firebase"),
        ("Who are the field agents?", "Should detect 'field agents' personnel and route to Firebase"),
        
        # Hybrid queries
        ("Which technician installed the most drops?", "Should detect both personnel and infrastructure"),
        
        # Telecom-specific queries
        ("Show PON utilization for Ivory Park", "Should detect PON and include utilization formula"),
        ("What's the optical power for drop LAW-001?", "Should detect measurement and project code"),
        ("Calculate average splice loss this month", "Should detect splice loss and temporal reference"),
        
        # Complex analytical queries
        ("What's the installation efficiency by project?", "Should detect business metrics"),
    ]
    
    results_summary = {
        'total': 0,
        'successful': 0,
        'failed': 0,
        'firebase_correct': 0,
        'postgresql_correct': 0,
        'entities_detected': 0
    }
    
    for query, expected in test_queries:
        print(f"\n{'='*70}")
        print(f"Testing: {query}")
        print(f"Expected: {expected}")
        
        result = test_query(query)
        results_summary['total'] += 1
        
        if result.get('success'):
            results_summary['successful'] += 1
            print("✅ Query executed successfully")
        elif "API not running" in str(result.get('error', '')):
            print("⚠️  API is not running. Please start it with: python3 api_enhanced.py")
            break
        else:
            results_summary['failed'] += 1
            print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
        
        # Check routing accuracy
        if result.get('query_classification'):
            databases = result['query_classification'].get('databases', [])
            if 'firebase' in databases and 'staff' in query.lower():
                results_summary['firebase_correct'] += 1
                print("✅ Correctly routed to Firebase")
            elif 'postgresql' in databases and any(term in query.lower() for term in ['drop', 'pole', 'project']):
                results_summary['postgresql_correct'] += 1
                print("✅ Correctly routed to PostgreSQL")
        
        # Check entity detection
        if result.get('entities_detected'):
            results_summary['entities_detected'] += 1
            print(f"✅ Entities detected: {list(result['entities_detected'].keys())}")
        
        time.sleep(0.5)  # Avoid overwhelming the API
    
    # Print summary
    print(f"\n{'='*70}")
    print("📊 TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total queries tested: {results_summary['total']}")
    print(f"Successful: {results_summary['successful']} ({results_summary['successful']/max(1, results_summary['total'])*100:.1f}%)")
    print(f"Failed: {results_summary['failed']}")
    print(f"Entity detection rate: {results_summary['entities_detected']}/{results_summary['total']} ({results_summary['entities_detected']/max(1, results_summary['total'])*100:.1f}%)")
    print(f"Firebase routing accuracy: {results_summary['firebase_correct']}")
    print(f"PostgreSQL routing accuracy: {results_summary['postgresql_correct']}")

def test_individual_query():
    """Test a single query interactively"""
    
    print("\n🔧 INTERACTIVE QUERY TESTER")
    print("="*70)
    print("Enter queries to test (type 'exit' to quit)")
    
    while True:
        query = input("\n> ").strip()
        if query.lower() in ['exit', 'quit', 'q']:
            break
        
        if not query:
            continue
        
        result = test_query(query)
        print_result(query, result)

def check_api_status():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        if response.status_code == 200:
            print("✅ API is running at", API_URL)
            return True
    except:
        pass
    
    print("❌ API is not running")
    print("\nTo start the API, run:")
    print("  python3 api_enhanced.py")
    return False

if __name__ == "__main__":
    print("🎯 FF_AGENT API INTEGRATION TEST")
    print("="*70)
    
    # Check API status
    if not check_api_status():
        print("\nPlease start the API first, then run this test again.")
        exit(1)
    
    # Run test suite
    print("\n1. Running automated test suite...")
    run_test_suite()
    
    # Offer interactive testing
    print("\n2. Would you like to test individual queries? (y/n)")
    if input("> ").lower() == 'y':
        test_individual_query()
    
    print("\n✅ Testing complete!")