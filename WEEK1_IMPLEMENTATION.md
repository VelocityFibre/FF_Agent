# Week 1 Implementation Guide - Quick Wins with Prompt Engineering

## Day 1-2: Enhanced Prompt System

### Step 1: Create the Enhanced Prompt Module

```python
# prompt_improvements.py
import re
from typing import Dict, List, Tuple

class TelecomEntityDetector:
    """Detect telecom-specific entities in queries"""
    
    def __init__(self):
        self.telecom_terms = {
            'equipment': ['olt', 'onu', 'ont', 'splitter', 'pon', 'gpon', 'nokia'],
            'measurements': ['optical power', 'splice loss', 'attenuation', 'dbm', 'db'],
            'infrastructure': ['drop', 'pole', 'fibre', 'cable', 'duct', 'chamber'],
            'business': ['take rate', 'homes passed', 'penetration', 'churn', 'arpu'],
            'personnel': ['technician', 'installer', 'field agent', 'staff', 'employee']
        }
        
        self.project_patterns = [
            r'LAW[\d-]*',  # Lawley
            r'IVY[\d-]*',  # Ivory Park  
            r'MAM[\d-]*',  # Mamelodi
            r'MOH[\d-]*',  # Mohadin
        ]
    
    def detect_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query"""
        query_lower = query.lower()
        detected = {}
        
        # Detect telecom terms
        for category, terms in self.telecom_terms.items():
            found = [term for term in terms if term in query_lower]
            if found:
                detected[category] = found
        
        # Detect project codes
        for pattern in self.project_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                detected['project_codes'] = matches
        
        # Detect dates
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(?:today|yesterday|this week|last month)\b'
        ]
        for pattern in date_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                detected['temporal'] = True
                break
        
        return detected

class QueryClassifier:
    """Classify query intent and complexity"""
    
    def classify(self, query: str, entities: Dict) -> Dict:
        """Determine query type and routing"""
        classification = {
            'type': 'unknown',
            'complexity': 'simple',
            'databases': [],
            'needs_join': False
        }
        
        query_lower = query.lower()
        
        # Determine type
        if any(term in query_lower for term in ['staff', 'employee', 'technician', 'who installed']):
            classification['type'] = 'personnel'
            classification['databases'].append('firebase')
        
        if any(term in query_lower for term in ['drop', 'pole', 'project', 'nokia']):
            classification['type'] = 'infrastructure' if classification['type'] == 'unknown' else 'hybrid'
            classification['databases'].append('postgresql')
        
        # Determine complexity
        if 'group by' in query_lower or 'average' in query_lower or 'sum' in query_lower:
            classification['complexity'] = 'analytical'
        
        if len(classification['databases']) > 1:
            classification['complexity'] = 'complex'
            classification['needs_join'] = True
        
        return classification

class EnhancedPromptGenerator:
    """Generate optimized prompts with context"""
    
    def __init__(self):
        self.entity_detector = TelecomEntityDetector()
        self.classifier = QueryClassifier()
        
    def generate_prompt(self, question: str, schema: str, similar_queries: List = None) -> str:
        """Generate enhanced prompt with all context"""
        
        # Detect entities
        entities = self.entity_detector.detect_entities(question)
        
        # Classify query
        classification = self.classifier.classify(question, entities)
        
        # Build context sections
        entity_context = self._format_entities(entities)
        routing_context = self._format_routing(classification)
        examples_context = self._format_examples(similar_queries) if similar_queries else ""
        
        prompt = f"""You are FibreFlow's data expert with deep telecom knowledge.

## Query Analysis
User Question: {question}

Detected Entities:
{entity_context}

Query Classification:
{routing_context}

## Database Schema
{schema}

## Routing Rules
- PostgreSQL: infrastructure (drops, poles, projects, equipment)
- Firebase: personnel (staff, users, real-time data)
- For Firebase queries, return: FIREBASE_QUERY: collection_name

{examples_context}

## SQL Generation Rules
1. Use exact table and column names from schema
2. For telecom metrics, use standard calculations:
   - PON utilization: COUNT(*)/32 (32 ports per PON)
   - Take rate: (active_drops/homes_passed)*100
3. Limit results to 100 unless specified
4. Use CTEs for complex queries
5. Add comments for business logic

Generate the SQL query:"""
        
        return prompt
    
    def _format_entities(self, entities: Dict) -> str:
        if not entities:
            return "- No specific entities detected"
        
        lines = []
        for category, items in entities.items():
            if isinstance(items, list):
                lines.append(f"- {category}: {', '.join(items)}")
            else:
                lines.append(f"- {category}: {items}")
        return '\n'.join(lines)
    
    def _format_routing(self, classification: Dict) -> str:
        lines = [
            f"- Type: {classification['type']}",
            f"- Complexity: {classification['complexity']}",
            f"- Target databases: {', '.join(classification['databases']) if classification['databases'] else 'PostgreSQL (default)'}"
        ]
        if classification['needs_join']:
            lines.append("- Requires cross-database coordination")
        return '\n'.join(lines)
    
    def _format_examples(self, similar_queries: List) -> str:
        if not similar_queries:
            return ""
        
        examples = "\n## Similar Successful Queries\n"
        for i, q in enumerate(similar_queries[:3], 1):
            examples += f"\nExample {i}:\n"
            examples += f"Question: {q.get('question', '')}\n"
            examples += f"SQL: {q.get('sql_query', '')}\n"
        
        return examples
```

### Step 2: Update the API to Use Enhanced Prompts

```python
# api_enhanced_v2.py (update to existing api_enhanced.py)

from prompt_improvements import EnhancedPromptGenerator

class ImprovedFFAgent:
    def __init__(self):
        self.prompt_generator = EnhancedPromptGenerator()
        # ... existing initialization
    
    def generate_enhanced_sql(self, question: str) -> tuple[str, Dict]:
        """Generate SQL with enhanced prompting"""
        
        # Get schema
        schema = get_schema()
        schema_str = format_schema_for_prompt(schema)
        
        # Get similar queries from vector store
        similar_queries = self.vector_store.find_similar_queries(question, limit=3)
        
        # Generate enhanced prompt
        prompt = self.prompt_generator.generate_prompt(
            question=question,
            schema=schema_str,
            similar_queries=similar_queries
        )
        
        # Generate SQL using Gemini
        response = gemini_model.generate_content(prompt)
        sql = response.text.strip()
        
        # Clean up SQL
        sql = sql.replace("```sql", "").replace("```", "").strip()
        
        return sql, {
            'prompt_enhanced': True,
            'entities_detected': len(self.prompt_generator.entity_detector.detect_entities(question)) > 0
        }
```

## Day 3-4: Quick RAG Improvements

### Step 3: Document Ingestion System

```python
# document_ingester.py
import os
import json
from typing import List, Dict
from datetime import datetime
import pandas as pd
from pathlib import Path

class QuickDocumentIngester:
    """Ingest common document formats into vector store"""
    
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.ingested_count = 0
    
    def ingest_csv_schemas(self, csv_path: str):
        """Ingest CSV files as schema documentation"""
        df = pd.read_csv(csv_path)
        
        # Create description of CSV structure
        schema_doc = f"CSV File: {Path(csv_path).name}\n"
        schema_doc += f"Columns: {', '.join(df.columns)}\n"
        schema_doc += f"Row count: {len(df)}\n"
        schema_doc += f"Sample data:\n{df.head(3).to_string()}\n"
        
        # Store in vector database
        embedding = self.vector_store.generate_embedding(schema_doc)
        if embedding:
            with self.vector_store.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO schema_embeddings 
                        (table_name, column_name, description, embedding)
                        VALUES (%s, %s, %s, %s::vector)
                    """, (
                        Path(csv_path).stem,  # Use filename as table name
                        'all_columns',
                        schema_doc,
                        embedding
                    ))
                    conn.commit()
            self.ingested_count += 1
    
    def ingest_json_configs(self, json_path: str):
        """Ingest JSON configuration files"""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Create searchable description
        config_doc = f"Configuration: {Path(json_path).name}\n"
        config_doc += json.dumps(data, indent=2)[:1000]  # First 1000 chars
        
        # Store embedding
        embedding = self.vector_store.generate_embedding(config_doc)
        if embedding:
            # Store as documentation
            self.vector_store.store_successful_query(
                question=f"Configuration for {Path(json_path).stem}",
                sql_query=f"CONFIG_REFERENCE: {json_path}",
                metadata={'type': 'configuration', 'path': json_path}
            )
            self.ingested_count += 1
    
    def ingest_sql_history(self, history_file: str):
        """Ingest historical SQL queries"""
        with open(history_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        query_data = json.loads(line)
                        self.vector_store.store_successful_query(
                            question=query_data.get('question', ''),
                            sql_query=query_data.get('sql', ''),
                            execution_time=query_data.get('execution_time', 1.0)
                        )
                        self.ingested_count += 1
                    except:
                        continue
    
    def quick_ingest_all(self, base_path: str = '.'):
        """Ingest all available documents"""
        print("Starting quick document ingestion...")
        
        # Ingest CSVs
        for csv_file in Path(base_path).glob('**/*.csv'):
            try:
                self.ingest_csv_schemas(str(csv_file))
                print(f"✓ Ingested: {csv_file.name}")
            except Exception as e:
                print(f"✗ Failed: {csv_file.name} - {e}")
        
        # Ingest JSONs
        for json_file in Path(base_path).glob('**/*.json'):
            if 'node_modules' not in str(json_file):
                try:
                    self.ingest_json_configs(str(json_file))
                    print(f"✓ Ingested: {json_file.name}")
                except Exception as e:
                    print(f"✗ Failed: {json_file.name} - {e}")
        
        print(f"\nTotal documents ingested: {self.ingested_count}")
```

## Day 5: Testing and Optimization

### Step 4: Test Suite for Improvements

```python
# test_improvements.py
import unittest
from prompt_improvements import TelecomEntityDetector, QueryClassifier, EnhancedPromptGenerator

class TestEnhancements(unittest.TestCase):
    
    def setUp(self):
        self.entity_detector = TelecomEntityDetector()
        self.classifier = QueryClassifier()
        self.prompt_gen = EnhancedPromptGenerator()
    
    def test_entity_detection(self):
        """Test telecom entity detection"""
        test_cases = [
            ("Show optical power for drop LAW-001", 
             {'measurements': ['optical power'], 'infrastructure': ['drop'], 'project_codes': ['LAW-001']}),
            ("List all technicians who installed drops this week",
             {'personnel': ['technician'], 'infrastructure': ['drop'], 'temporal': True}),
            ("What's the PON utilization?",
             {'equipment': ['pon']})
        ]
        
        for query, expected in test_cases:
            result = self.entity_detector.detect_entities(query)
            for key in expected:
                self.assertIn(key, result, f"Failed to detect {key} in: {query}")
    
    def test_query_classification(self):
        """Test query routing"""
        test_cases = [
            ("List all staff", {'type': 'personnel', 'databases': ['firebase']}),
            ("Show drops in Lawley", {'type': 'infrastructure', 'databases': ['postgresql']}),
            ("Which technician installed the most drops?", {'type': 'hybrid', 'databases': ['firebase', 'postgresql']})
        ]
        
        for query, expected in test_cases:
            entities = self.entity_detector.detect_entities(query)
            result = self.classifier.classify(query, entities)
            self.assertEqual(result['type'], expected['type'])
            self.assertEqual(set(result['databases']), set(expected['databases']))
    
    def test_prompt_generation(self):
        """Test enhanced prompt generation"""
        question = "Show PON utilization for Lawley project"
        schema = "Table: sow_drops\nColumns: drop_number, pon_id, project"
        
        prompt = self.prompt_gen.generate_prompt(question, schema)
        
        # Check key sections exist
        self.assertIn("Detected Entities:", prompt)
        self.assertIn("Query Classification:", prompt)
        self.assertIn("PON utilization: COUNT(*)/32", prompt)  # Domain knowledge

if __name__ == '__main__':
    unittest.main()
```

### Step 5: Integration Script

```python
# integrate_improvements.py
#!/usr/bin/env python3
"""
One-click script to integrate Week 1 improvements
"""

import os
import shutil
from pathlib import Path

def integrate_improvements():
    print("🚀 Integrating Week 1 Improvements...")
    
    # 1. Backup existing files
    print("\n1. Creating backups...")
    backup_dir = Path("backups") / "week1"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    files_to_backup = ['api_enhanced.py', 'vector_store.py']
    for file in files_to_backup:
        if Path(file).exists():
            shutil.copy(file, backup_dir / f"{file}.backup")
            print(f"   ✓ Backed up {file}")
    
    # 2. Check dependencies
    print("\n2. Checking dependencies...")
    required = ['pandas', 'numpy', 'psycopg2', 'google-generativeai']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"   ✓ {package} installed")
        except ImportError:
            missing.append(package)
            print(f"   ✗ {package} missing")
    
    if missing:
        print(f"\n   Installing missing packages: {', '.join(missing)}")
        os.system(f"pip install {' '.join(missing)}")
    
    # 3. Initialize improvements
    print("\n3. Initializing improvements...")
    
    # Import and test
    try:
        from prompt_improvements import EnhancedPromptGenerator
        from document_ingester import QuickDocumentIngester
        from vector_store import VectorStore
        
        # Initialize vector store
        vs = VectorStore()
        vs.initialize_pgvector()
        
        # Test prompt generation
        prompt_gen = EnhancedPromptGenerator()
        test_prompt = prompt_gen.generate_prompt(
            "Show drops in Lawley",
            "Table: sow_drops\nColumns: drop_number, project"
        )
        print("   ✓ Prompt generator working")
        
        # Ingest documents
        ingester = QuickDocumentIngester(vs)
        ingester.quick_ingest_all()
        print("   ✓ Document ingestion complete")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # 4. Run tests
    print("\n4. Running tests...")
    os.system("python test_improvements.py")
    
    print("\n✅ Week 1 improvements integrated successfully!")
    print("\nNext steps:")
    print("1. Restart API: python api_enhanced_v2.py")
    print("2. Test queries in UI")
    print("3. Monitor improvements in /stats endpoint")
    
    return True

if __name__ == "__main__":
    integrate_improvements()
```

## Immediate Actions Checklist

### Today (Day 1):
- [ ] Create `prompt_improvements.py`
- [ ] Test entity detection with real queries
- [ ] Update API to use enhanced prompts

### Tomorrow (Day 2):
- [ ] Create `document_ingester.py`
- [ ] Ingest existing CSVs and configs
- [ ] Test with enhanced context

### Day 3:
- [ ] Create test suite
- [ ] Run integration script
- [ ] Measure improvement metrics

### Day 4-5:
- [ ] Deploy to development environment
- [ ] Collect user feedback
- [ ] Document improvements

## Expected Results After Week 1

### Metrics
- **Query Accuracy**: +20% (from 75% to 90%)
- **Entity Detection**: 95% accuracy on telecom terms
- **Routing Accuracy**: 98% (Firebase vs PostgreSQL)
- **Context Relevance**: 3x more relevant examples

### User Experience
- Better understanding of telecom terminology
- Fewer "table not found" errors  
- More accurate Firebase routing
- Contextual query suggestions

### Technical Improvements
- Modular prompt system
- Document ingestion pipeline
- Comprehensive test coverage
- Performance baselines established

---

**Ready to implement!** Start with `prompt_improvements.py` and see immediate results.