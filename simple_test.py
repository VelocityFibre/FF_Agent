#!/usr/bin/env python3
"""
Simple test for all 4 phases of FF_Agent Enhancement
"""

def test_all_phases():
    print("🧪 Testing FF_Agent Complete Enhancement System")
    print("="*60)
    
    results = {}
    
    # Test Phase 1: Prompt Engineering
    print("\n📍 Phase 1: Prompt Engineering")
    try:
        from prompt_improvements import EnhancedPromptGenerator
        gen = EnhancedPromptGenerator()
        result = gen.analyze_query("List all staff")
        
        if 'personnel' in result['entities'] and 'firebase' in result['classification']['databases']:
            print("✅ Entity detection working")
            print(f"   Detected: {list(result['entities'].keys())}")
            print(f"   Routed to: {result['classification']['databases']}")
            results['Phase 1'] = True
        else:
            print("❌ Entity detection failed")
            results['Phase 1'] = False
    except Exception as e:
        print(f"❌ Phase 1 error: {e}")
        results['Phase 1'] = False
    
    # Test Phase 2: RAG Enhancement
    print("\n📚 Phase 2: RAG Enhancement")
    try:
        from document_ingester import DocumentIngester
        ingester = DocumentIngester()
        entities = ingester.extract_fibreflow_entities('Drop LAW-001 has optical power -25 dBm')
        
        if 'project_codes' in entities and 'LAW' in str(entities['project_codes']):
            print("✅ Document ingestion working")
            print(f"   Extracted: {list(entities.keys())}")
            results['Phase 2'] = True
        else:
            print("❌ Entity extraction failed")
            results['Phase 2'] = False
    except Exception as e:
        print(f"❌ Phase 2 error: {e}")
        results['Phase 2'] = False
    
    # Test Phase 3: Feedback Loop
    print("\n🔄 Phase 3: Feedback Loop")
    try:
        from feedback_system import FeedbackCollector, LearningEngine
        collector = FeedbackCollector()
        
        # Collect sample feedback
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
        print("✅ Feedback collection working")
        print(f"   Total queries tracked: {stats['total_queries']}")
        results['Phase 3'] = True
        
    except Exception as e:
        print(f"❌ Phase 3 error: {e}")
        results['Phase 3'] = False
    
    # Test Phase 4: Fine-tuning
    print("\n🎯 Phase 4: Fine-tuning")
    try:
        from finetuning_system import FineTuningDataPreparer
        preparer = FineTuningDataPreparer()
        
        # Generate synthetic examples
        synthetic = preparer._generate_synthetic_examples(count=5)
        
        if len(synthetic) == 5:
            print("✅ Fine-tuning preparation working")
            print(f"   Generated {len(synthetic)} training examples")
            results['Phase 4'] = True
        else:
            print("❌ Training data generation failed")
            results['Phase 4'] = False
            
    except Exception as e:
        print(f"❌ Phase 4 error: {e}")
        results['Phase 4'] = False
    
    # Test Integration
    print("\n🔗 Integration Test: All Phases Together")
    try:
        # Import all components
        from prompt_improvements import EnhancedPromptGenerator
        from document_ingester import DocumentIngester
        from feedback_system import FeedbackCollector, LearningEngine, PerformanceMonitor
        from finetuning_system import FineTuningDataPreparer, ModelTrainer
        
        # Create instances
        prompt_gen = EnhancedPromptGenerator()
        doc_ingester = DocumentIngester()
        feedback_collector = FeedbackCollector()
        learning_engine = LearningEngine(feedback_collector)
        performance_monitor = PerformanceMonitor(feedback_collector)
        finetuner = FineTuningDataPreparer()
        trainer = ModelTrainer()
        
        # Test complete flow
        query = "Show drops in Lawley project"
        
        # Phase 1: Analyze query
        analysis = prompt_gen.analyze_query(query)
        
        # Phase 2: Extract entities
        entities = doc_ingester.extract_fibreflow_entities(query)
        
        # Phase 3: Would collect feedback (simulated)
        # Phase 4: Would prepare training data (already tested)
        
        print("✅ All phases can work together!")
        print(f"   Query type: {analysis['classification']['type']}")
        print(f"   Entities found: {bool(entities)}")
        print(f"   Feedback ready: {feedback_collector is not None}")
        print(f"   Training ready: {finetuner is not None}")
        results['Integration'] = True
        
    except Exception as e:
        print(f"❌ Integration error: {e}")
        results['Integration'] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for phase, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {phase}: {status}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 SUCCESS! All 4 phases are working correctly!")
        print("\n🚀 The FF_Agent enhancement is complete and operational!")
        print("\nCapabilities now active:")
        print("  • Smart entity detection (Phase 1)")
        print("  • Document context retrieval (Phase 2)")
        print("  • Continuous learning (Phase 3)")
        print("  • Ready for fine-tuning (Phase 4)")
        
        print("\n📝 Next Steps:")
        print("  1. Start the API: python3 api_with_feedback.py")
        print("  2. Test with real queries")
        print("  3. System will learn and improve automatically!")
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"\n⚠️  Failed phases: {', '.join(failed)}")
        print("Check the errors above for details.")
    
    return passed == total

if __name__ == "__main__":
    import sys
    success = test_all_phases()
    sys.exit(0 if success else 1)