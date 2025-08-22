#!/usr/bin/env python3
"""
Test script for FF_Agent Integrated System
Tests the integration without requiring full dependencies
"""

import os
import json
from datetime import datetime

def test_feedback_system():
    """Test the feedback system"""
    print("🧪 Testing Feedback System...")
    
    try:
        from feedback_system import FeedbackSystem
        
        # Create a test feedback system
        fs = FeedbackSystem("test_feedback")
        
        # Test logging a query
        query_id = fs.log_query(
            question="Test query",
            sql="SELECT * FROM test",
            success=True,
            method="test"
        )
        
        print(f"✅ Query logged with ID: {query_id}")
        
        # Test recording feedback
        fs.record_feedback(
            query_id=query_id,
            was_correct=True,
            feedback="Good result"
        )
        
        print("✅ Feedback recorded")
        
        # Test getting stats
        stats = fs.get_stats()
        print(f"✅ Stats retrieved: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Feedback system test failed: {e}")
        return False

def test_api_structure():
    """Test the API structure"""
    print("\n🧪 Testing API Structure...")
    
    try:
        # Read the integrated API file
        with open('api_integrated.py', 'r') as f:
            content = f.read()
        
        # Check for key components
        components = [
            'FFAgentVanna',
            'CachedVectorStore', 
            'FeedbackSystem',
            '/query',
            '/feedback',
            '/suggestions',
            '/stats'
        ]
        
        missing = []
        for component in components:
            if component not in content:
                missing.append(component)
        
        if missing:
            print(f"❌ Missing components: {missing}")
            return False
        else:
            print("✅ All API components present")
            return True
            
    except Exception as e:
        print(f"❌ API structure test failed: {e}")
        return False

def test_ui_enhancements():
    """Test UI enhancements"""
    print("\n🧪 Testing UI Enhancements...")
    
    try:
        with open('ui/index.html', 'r') as f:
            content = f.read()
        
        # Check for enhanced features
        features = [
            'suggestions',
            'feedback',
            'method_used',
            'confidence',
            'similar_patterns',
            'FF_Agent Enhanced'
        ]
        
        missing = []
        for feature in features:
            if feature not in content:
                missing.append(feature)
        
        if missing:
            print(f"❌ Missing UI features: {missing}")
            return False
        else:
            print("✅ All UI enhancements present")
            return True
            
    except Exception as e:
        print(f"❌ UI enhancement test failed: {e}")
        return False

def generate_test_report():
    """Generate integration test report"""
    print("\n📋 FF_Agent Integration Test Report")
    print("=" * 50)
    
    tests = [
        ("Feedback System", test_feedback_system),
        ("API Structure", test_api_structure), 
        ("UI Enhancements", test_ui_enhancements)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
                failed += 1
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All integration tests passed!")
        print("\n🚀 System ready for deployment:")
        print("   1. Install dependencies: pip install vanna chromadb psycopg2 fastapi uvicorn")
        print("   2. Set environment variables (DATABASE_URL, GOOGLE_API_KEY)")
        print("   3. Run: ./start_integrated_system.sh")
        print("   4. Open UI: http://localhost:3000")
    else:
        print(f"\n⚠️  {failed} integration issues found")
    
    return failed == 0

if __name__ == "__main__":
    generate_test_report()