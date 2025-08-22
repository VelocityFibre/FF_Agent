#!/usr/bin/env python3
"""
Enhanced Prompt System for FF_Agent
Implements telecom entity detection, query classification, and context-aware prompt generation
"""

import re
from typing import Dict, List, Tuple, Optional

class TelecomEntityDetector:
    """Detect telecom-specific entities in queries"""
    
    def __init__(self):
        self.telecom_terms = {
            'equipment': ['olt', 'onu', 'ont', 'splitter', 'pon', 'gpon', 'nokia', 'fiber', 'fibre'],
            'measurements': ['optical power', 'splice loss', 'attenuation', 'dbm', 'db', 'signal strength'],
            'infrastructure': ['drop', 'pole', 'fibre', 'cable', 'duct', 'chamber', 'closure', 'splice'],
            'business': ['take rate', 'homes passed', 'penetration', 'churn', 'arpu', 'installation', 'activation'],
            'personnel': ['technician', 'installer', 'field agent', 'staff', 'employee', 'team', 'crew']
        }
        
        # FibreFlow specific project patterns
        self.project_patterns = [
            (r'LAW[\d-]*', 'Lawley'),
            (r'IVY[\d-]*', 'Ivory Park'),
            (r'MAM[\d-]*', 'Mamelodi'),
            (r'MOH[\d-]*', 'Mohadin'),
            (r'HEIN[\d-]*', 'Hein Test'),
        ]
        
        # Status values commonly used in the system
        self.status_values = [
            'active', 'inactive', 'pending', 'installed', 'not installed',
            'completed', 'in progress', 'scheduled', 'cancelled'
        ]
    
    def detect_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract entities from query"""
        query_lower = query.lower()
        detected = {}
        
        # Detect telecom terms
        for category, terms in self.telecom_terms.items():
            found = []
            for term in terms:
                if term in query_lower:
                    found.append(term)
            if found:
                detected[category] = found
        
        # Detect project codes and names
        project_codes = []
        project_names = []
        for pattern, name in self.project_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                project_codes.extend(matches)
                project_names.append(name)
            # Also check for project name mentions
            if name.lower() in query_lower:
                project_names.append(name)
        
        if project_codes:
            detected['project_codes'] = list(set(project_codes))
        if project_names:
            detected['project_names'] = list(set(project_names))
        
        # Detect status values
        found_status = [status for status in self.status_values if status in query_lower]
        if found_status:
            detected['status_values'] = found_status
        
        # Detect temporal references
        temporal_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b(?:today|yesterday|tomorrow)\b',
            r'\b(?:this|last|next)\s+(?:week|month|year|quarter)\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b\d+\s+(?:days?|weeks?|months?|years?)\s+ago\b'
        ]
        
        for pattern in temporal_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                detected['temporal'] = True
                break
        
        # Detect numeric values and ranges
        numeric_patterns = [
            r'\b\d+\b',
            r'\btop\s+\d+\b',
            r'\b(?:more|less|greater|fewer)\s+than\s+\d+\b',
            r'\bbetween\s+\d+\s+and\s+\d+\b'
        ]
        
        numeric_values = []
        for pattern in numeric_patterns:
            matches = re.findall(pattern, query_lower)
            numeric_values.extend(matches)
        
        if numeric_values:
            detected['numeric'] = numeric_values
        
        # Detect aggregation keywords
        aggregations = ['count', 'sum', 'average', 'avg', 'total', 'max', 'min', 'group by']
        found_agg = [agg for agg in aggregations if agg in query_lower]
        if found_agg:
            detected['aggregations'] = found_agg
        
        return detected

class QueryClassifier:
    """Classify query intent and complexity"""
    
    def classify(self, query: str, entities: Dict) -> Dict:
        """Determine query type and routing"""
        classification = {
            'type': 'unknown',
            'complexity': 'simple',
            'databases': [],
            'needs_join': False,
            'is_analytical': False,
            'is_real_time': False
        }
        
        query_lower = query.lower()
        
        # Determine primary type based on entities and keywords
        
        # Personnel queries
        if 'personnel' in entities or any(term in query_lower for term in ['staff', 'employee', 'technician', 'who installed', 'who worked', 'assigned to']):
            classification['type'] = 'personnel'
            classification['databases'].append('firebase')
        
        # Infrastructure queries
        if any(key in entities for key in ['infrastructure', 'equipment', 'measurements']):
            if classification['type'] == 'personnel':
                classification['type'] = 'hybrid'
            else:
                classification['type'] = 'infrastructure'
            classification['databases'].append('postgresql')
        
        # Project queries
        if 'project_codes' in entities or 'project_names' in entities or 'project' in query_lower:
            if classification['type'] == 'unknown':
                classification['type'] = 'project'
            classification['databases'].append('postgresql')
        
        # Business/analytical queries
        if 'business' in entities or 'aggregations' in entities:
            classification['is_analytical'] = True
            if classification['type'] == 'unknown':
                classification['type'] = 'analytical'
        
        # Real-time queries
        if any(term in query_lower for term in ['current', 'now', 'active', 'real-time', 'live', 'ongoing']):
            classification['is_real_time'] = True
        
        # Determine complexity
        if 'aggregations' in entities:
            classification['complexity'] = 'moderate' if len(entities.get('aggregations', [])) == 1 else 'complex'
        
        if len(classification['databases']) > 1:
            classification['complexity'] = 'complex'
            classification['needs_join'] = True
        
        if any(term in query_lower for term in ['join', 'combine', 'match', 'correlate']):
            classification['complexity'] = 'complex'
            classification['needs_join'] = True
        
        # Default to PostgreSQL if no specific database identified
        if not classification['databases']:
            classification['databases'].append('postgresql')
            classification['type'] = 'general' if classification['type'] == 'unknown' else classification['type']
        
        return classification

class EnhancedPromptGenerator:
    """Generate optimized prompts with context"""
    
    def __init__(self):
        self.entity_detector = TelecomEntityDetector()
        self.classifier = QueryClassifier()
        
    def generate_prompt(self, question: str, schema: str, similar_queries: List = None, error_patterns: List = None) -> str:
        """Generate enhanced prompt with all context"""
        
        # Detect entities
        entities = self.entity_detector.detect_entities(question)
        
        # Classify query
        classification = self.classifier.classify(question, entities)
        
        # Build context sections
        entity_context = self._format_entities(entities)
        routing_context = self._format_routing(classification)
        examples_context = self._format_examples(similar_queries) if similar_queries else ""
        errors_context = self._format_errors(error_patterns) if error_patterns else ""
        domain_hints = self._get_domain_hints(entities, classification)
        
        prompt = f"""You are FibreFlow's data expert with deep telecommunications knowledge.

## Query Analysis
User Question: {question}

Detected Entities:
{entity_context}

Query Classification:
{routing_context}

## Database Schema
{schema}

## Routing Rules
- PostgreSQL (Neon): infrastructure data
  * Tables: projects, sow_drops, sow_poles, sow_fibre, nokia_data, status_changes
  * Use for: drops, poles, equipment, installations, project data
  
- Firebase: personnel and real-time data
  * Collections: staff, users, active_installations, alerts
  * Use for: employee data, technician assignments, real-time updates
  * Return format: FIREBASE_QUERY: collection_name

{domain_hints}

{examples_context}

{errors_context}

## SQL Generation Rules
1. Use EXACT table and column names from the schema
2. For telecom calculations use:
   - PON utilization: (COUNT(*) * 100.0 / 32) for 32-port PON
   - Take rate: (active_drops * 100.0 / homes_passed)
   - Splice loss: typically measured in dB (decibels)
3. Always limit results to 100 unless specified otherwise
4. Use CTEs for complex multi-step queries
5. Add SQL comments for business logic
6. For date ranges, use PostgreSQL date functions
7. For Firebase queries, return: FIREBASE_QUERY: collection_name

Generate the SQL query:"""
        
        return prompt
    
    def _format_entities(self, entities: Dict) -> str:
        """Format detected entities for prompt"""
        if not entities:
            return "- No specific entities detected"
        
        lines = []
        for category, items in entities.items():
            if category == 'temporal':
                lines.append(f"- Temporal reference: Yes")
            elif isinstance(items, list):
                lines.append(f"- {category.replace('_', ' ').title()}: {', '.join(items)}")
            else:
                lines.append(f"- {category.replace('_', ' ').title()}: {items}")
        return '\n'.join(lines)
    
    def _format_routing(self, classification: Dict) -> str:
        """Format routing classification for prompt"""
        lines = [
            f"- Query Type: {classification['type']}",
            f"- Complexity: {classification['complexity']}",
            f"- Target Database(s): {', '.join(classification['databases'])}"
        ]
        
        if classification['needs_join']:
            lines.append("- Note: Requires cross-database coordination")
        if classification['is_analytical']:
            lines.append("- Note: Analytical query - use appropriate aggregations")
        if classification['is_real_time']:
            lines.append("- Note: Real-time data requested - consider Firebase")
        
        return '\n'.join(lines)
    
    def _format_examples(self, similar_queries: List) -> str:
        """Format similar query examples"""
        if not similar_queries:
            return ""
        
        examples = "\n## Similar Successful Queries (for reference)\n"
        for i, q in enumerate(similar_queries[:3], 1):
            examples += f"\nExample {i}:\n"
            examples += f"Question: {q.get('question', '')}\n"
            examples += f"SQL: {q.get('sql_query', '')[:200]}...\n" if len(q.get('sql_query', '')) > 200 else f"SQL: {q.get('sql_query', '')}\n"
            if 'success_rate' in q:
                examples += f"Success Rate: {q['success_rate']:.0%}\n"
        
        return examples
    
    def _format_errors(self, error_patterns: List) -> str:
        """Format error patterns to avoid"""
        if not error_patterns:
            return ""
        
        errors = "\n## Common Errors to Avoid\n"
        for i, err in enumerate(error_patterns[:2], 1):
            errors += f"\nError Pattern {i}:\n"
            errors += f"Failed Query: {err.get('attempted_sql', '')[:100]}...\n"
            errors += f"Error: {err.get('error_message', '')[:100]}...\n"
        
        return errors
    
    def _get_domain_hints(self, entities: Dict, classification: Dict) -> str:
        """Get domain-specific hints based on entities"""
        hints = []
        
        if 'measurements' in entities:
            hints.append("\n## Measurement Hints")
            if 'optical power' in entities.get('measurements', []):
                hints.append("- Optical power: typically stored in 'optical_power_db' column, measured in dBm")
            if 'splice loss' in entities.get('measurements', []):
                hints.append("- Splice loss: typically stored in 'splice_loss_db' column, acceptable range 0.1-0.5 dB")
        
        if 'project_codes' in entities or 'project_names' in entities:
            hints.append("\n## Project Hints")
            hints.append("- Project codes are prefixes in drop_number and pole_number columns")
            hints.append("- Use LIKE 'PREFIX%' for project filtering")
        
        if classification['is_analytical']:
            hints.append("\n## Analytical Query Hints")
            hints.append("- Use DATE_TRUNC for time-based grouping")
            hints.append("- Include NULL checks for aggregations")
            hints.append("- Consider using COALESCE for missing values")
        
        return '\n'.join(hints) if hints else ""

    def analyze_query(self, question: str) -> Dict:
        """Analyze a query and return detailed information"""
        entities = self.entity_detector.detect_entities(question)
        classification = self.classifier.classify(question, entities)
        
        return {
            'question': question,
            'entities': entities,
            'classification': classification,
            'recommended_database': classification['databases'][0] if classification['databases'] else 'postgresql',
            'complexity_score': self._calculate_complexity_score(entities, classification)
        }
    
    def _calculate_complexity_score(self, entities: Dict, classification: Dict) -> int:
        """Calculate a complexity score from 1-10"""
        score = 1
        
        # Add points for complexity factors
        if classification['complexity'] == 'moderate':
            score += 2
        elif classification['complexity'] == 'complex':
            score += 4
        
        if classification['needs_join']:
            score += 2
        
        if 'aggregations' in entities:
            score += len(entities['aggregations'])
        
        if classification['is_analytical']:
            score += 1
        
        if len(classification['databases']) > 1:
            score += 2
        
        return min(score, 10)


# Utility function for testing
def test_entity_detection():
    """Test the entity detection with sample queries"""
    detector = TelecomEntityDetector()
    
    test_queries = [
        "Show optical power for drop LAW-001",
        "List all technicians who installed drops this week",
        "What's the PON utilization in Lawley?",
        "Show me the top 10 poles with the most drops",
        "Which staff member installed drops in Ivory Park last month?",
        "Calculate average splice loss for Mamelodi project",
        "Show active Nokia equipment",
        "List employees assigned to field work"
    ]
    
    print("Entity Detection Test Results:\n" + "="*50)
    
    for query in test_queries:
        entities = detector.detect_entities(query)
        print(f"\nQuery: {query}")
        print(f"Entities: {entities}")
    
    return True


def test_query_classification():
    """Test query classification"""
    generator = EnhancedPromptGenerator()
    
    test_queries = [
        "Show all drops in Lawley",
        "List all staff members",
        "Which technician installed the most drops?",
        "Show PON utilization by project",
        "Get current active installations"
    ]
    
    print("\nQuery Classification Test Results:\n" + "="*50)
    
    for query in test_queries:
        analysis = generator.analyze_query(query)
        print(f"\nQuery: {query}")
        print(f"Type: {analysis['classification']['type']}")
        print(f"Complexity: {analysis['classification']['complexity']} (Score: {analysis['complexity_score']}/10)")
        print(f"Database(s): {', '.join(analysis['classification']['databases'])}")
        print(f"Entities: {list(analysis['entities'].keys())}")
    
    return True


if __name__ == "__main__":
    # Run tests when module is executed directly
    print("Testing Enhanced Prompt System for FF_Agent\n")
    
    # Test entity detection
    test_entity_detection()
    
    # Test query classification
    test_query_classification()
    
    print("\n✅ All tests completed successfully!")