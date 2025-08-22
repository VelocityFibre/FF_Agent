"""
Batch Learning Script - Efficiently learns patterns from all tables
Optimized for speed with minimal API calls
"""

import os
import json
from datetime import datetime
from typing import List, Dict
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import time

load_dotenv()

class BatchTableLearner:
    def __init__(self):
        self.engine = create_engine(os.getenv('NEON_DATABASE_URL'))
        self.patterns = []
        self.table_analysis = {}
        
    def analyze_all_tables(self) -> Dict:
        """Analyze all tables in the database"""
        print("📊 Analyzing all tables in database...")
        
        with self.engine.connect() as conn:
            # Get all tables
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            print(f"Found {len(tables)} tables to analyze")
            
            for table in tables:
                print(f"\n🔍 Analyzing: {table}")
                
                # Get table structure
                col_result = conn.execute(text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                
                columns = []
                has_dates = False
                has_status = False
                has_ids = False
                numeric_cols = []
                text_cols = []
                
                for col in col_result:
                    col_name, col_type, nullable = col
                    columns.append(col_name)
                    
                    # Classify columns
                    if 'date' in col_type or 'time' in col_type:
                        has_dates = True
                    if 'status' in col_name.lower():
                        has_status = True
                    if col_name.endswith('_id') or col_name == 'id':
                        has_ids = True
                    if col_type in ['integer', 'numeric', 'real', 'double precision']:
                        numeric_cols.append(col_name)
                    if col_type in ['text', 'character varying', 'varchar']:
                        text_cols.append(col_name)
                
                # Get row count
                try:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    row_count = count_result.scalar()
                except:
                    row_count = 0
                
                self.table_analysis[table] = {
                    'columns': columns,
                    'row_count': row_count,
                    'has_dates': has_dates,
                    'has_status': has_status,
                    'has_ids': has_ids,
                    'numeric_cols': numeric_cols[:3],  # Limit to 3
                    'text_cols': text_cols[:3]
                }
                
                print(f"  • Columns: {len(columns)}")
                print(f"  • Rows: {row_count}")
                print(f"  • Features: {'📅' if has_dates else ''} {'📊' if has_status else ''} {'🔑' if has_ids else ''}")
        
        return self.table_analysis
    
    def generate_patterns_for_table(self, table: str, info: Dict) -> List[Dict]:
        """Generate query patterns based on table structure"""
        patterns = []
        
        # Skip empty tables
        if info['row_count'] == 0:
            return patterns
        
        # Basic patterns - everyone gets these
        patterns.extend([
            {
                'question': f"Show all {table}",
                'sql': f"SELECT * FROM {table}",
                'type': 'basic'
            },
            {
                'question': f"Count {table} records",
                'sql': f"SELECT COUNT(*) as total FROM {table}",
                'type': 'basic'
            },
            {
                'question': f"Show first 10 {table}",
                'sql': f"SELECT * FROM {table} LIMIT 10",
                'type': 'basic'
            }
        ])
        
        # Date-based patterns
        if info['has_dates']:
            date_col = next((c for c in info['columns'] if 'date' in c.lower() or 'time' in c.lower()), 'created_at')
            patterns.extend([
                {
                    'question': f"Show recent {table}",
                    'sql': f"SELECT * FROM {table} WHERE {date_col} >= CURRENT_DATE - INTERVAL '7 days'",
                    'type': 'date'
                },
                {
                    'question': f"Get {table} from this month",
                    'sql': f"SELECT * FROM {table} WHERE {date_col} >= DATE_TRUNC('month', CURRENT_DATE)",
                    'type': 'date'
                },
                {
                    'question': f"Show {table} ordered by date",
                    'sql': f"SELECT * FROM {table} ORDER BY {date_col} DESC LIMIT 50",
                    'type': 'date'
                }
            ])
        
        # Status-based patterns
        if info['has_status']:
            status_col = next((c for c in info['columns'] if 'status' in c.lower()), 'status')
            patterns.extend([
                {
                    'question': f"Group {table} by status",
                    'sql': f"SELECT {status_col}, COUNT(*) as count FROM {table} GROUP BY {status_col}",
                    'type': 'status'
                },
                {
                    'question': f"Show active {table}",
                    'sql': f"SELECT * FROM {table} WHERE {status_col} = 'active'",
                    'type': 'status'
                },
                {
                    'question': f"Find pending {table}",
                    'sql': f"SELECT * FROM {table} WHERE {status_col} = 'pending'",
                    'type': 'status'
                }
            ])
        
        # Numeric aggregations
        for num_col in info['numeric_cols'][:2]:  # Limit to 2 numeric columns
            patterns.extend([
                {
                    'question': f"Calculate total {num_col} in {table}",
                    'sql': f"SELECT SUM({num_col}) as total FROM {table}",
                    'type': 'aggregation'
                },
                {
                    'question': f"Get average {num_col} from {table}",
                    'sql': f"SELECT AVG({num_col}) as average FROM {table}",
                    'type': 'aggregation'
                }
            ])
        
        # Text search patterns
        for text_col in info['text_cols'][:1]:  # Just one text column
            patterns.append({
                'question': f"Search {table} by {text_col}",
                'sql': f"SELECT * FROM {table} WHERE {text_col} ILIKE '%search_term%'",
                'type': 'search'
            })
        
        # ID-based patterns
        if info['has_ids']:
            id_col = next((c for c in info['columns'] if c == 'id' or c.endswith('_id')), 'id')
            patterns.append({
                'question': f"Find {table} by ID",
                'sql': f"SELECT * FROM {table} WHERE {id_col} = :id",
                'type': 'lookup'
            })
        
        return patterns
    
    def generate_all_patterns(self) -> List[Dict]:
        """Generate patterns for all tables"""
        print("\n🎯 Generating query patterns...")
        
        all_patterns = []
        pattern_stats = {}
        
        for table, info in self.table_analysis.items():
            table_patterns = self.generate_patterns_for_table(table, info)
            
            if table_patterns:
                all_patterns.extend(table_patterns)
                pattern_stats[table] = len(table_patterns)
                print(f"  ✅ {table}: {len(table_patterns)} patterns")
            else:
                print(f"  ⏭️  {table}: Skipped (empty)")
        
        # Add some complex cross-table patterns
        all_patterns.extend(self.generate_complex_patterns())
        
        print(f"\n📊 Total patterns generated: {len(all_patterns)}")
        return all_patterns
    
    def generate_complex_patterns(self) -> List[Dict]:
        """Generate complex patterns involving multiple tables"""
        complex = []
        
        # OneMap specific patterns
        if 'onemap_property_data' in self.table_analysis and 'onemap_fibre_data' in self.table_analysis:
            complex.append({
                'question': "Show properties with their fibre status",
                'sql': """SELECT p.*, f.status as fibre_status 
                         FROM onemap_property_data p 
                         LEFT JOIN onemap_fibre_data f ON p.property_id = f.property_id""",
                'type': 'join'
            })
        
        if 'onemap_import_batches' in self.table_analysis and 'onemap_status_history' in self.table_analysis:
            complex.append({
                'question': "Show import batches with their latest status",
                'sql': """SELECT b.*, h.status as latest_status 
                         FROM onemap_import_batches b 
                         JOIN onemap_status_history h ON b.id = h.import_batch_id
                         WHERE h.change_date = (
                             SELECT MAX(change_date) 
                             FROM onemap_status_history 
                             WHERE import_batch_id = b.id
                         )""",
                'type': 'complex_join'
            })
        
        # Connection test patterns
        if 'connection_tests' in self.table_analysis:
            complex.append({
                'question': "Show connection test success rate by day",
                'sql': """SELECT DATE(tested_at) as test_date, 
                                COUNT(*) as total_tests,
                                SUM(CASE WHEN test_result = 'success' THEN 1 ELSE 0 END) as successful,
                                AVG(CASE WHEN test_result = 'success' THEN 1.0 ELSE 0.0 END) * 100 as success_rate
                         FROM connection_tests
                         GROUP BY DATE(tested_at)
                         ORDER BY test_date DESC""",
                'type': 'analytical'
            })
        
        return complex
    
    def save_patterns(self, patterns: List[Dict]):
        """Save patterns to JSON file for batch import"""
        filename = f"patterns_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_patterns': len(patterns),
                'tables_analyzed': len(self.table_analysis),
                'patterns': patterns
            }, f, indent=2)
        
        print(f"\n💾 Patterns saved to: {filename}")
        return filename
    
    def run(self):
        """Run the complete batch learning process"""
        print("🚀 Starting Batch Table Learning")
        print("=" * 50)
        
        start_time = time.time()
        
        # Analyze all tables
        self.analyze_all_tables()
        
        # Generate patterns
        patterns = self.generate_all_patterns()
        
        # Save patterns
        filename = self.save_patterns(patterns)
        
        elapsed = time.time() - start_time
        
        print("\n" + "=" * 50)
        print("✅ Batch Learning Complete!")
        print(f"  • Tables analyzed: {len(self.table_analysis)}")
        print(f"  • Patterns generated: {len(patterns)}")
        print(f"  • Time taken: {elapsed:.2f} seconds")
        print(f"  • Output file: {filename}")
        
        # Summary by pattern type
        pattern_types = {}
        for p in patterns:
            p_type = p.get('type', 'unknown')
            pattern_types[p_type] = pattern_types.get(p_type, 0) + 1
        
        print("\n📊 Pattern Distribution:")
        for p_type, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {p_type}: {count}")
        
        return patterns

if __name__ == "__main__":
    learner = BatchTableLearner()
    patterns = learner.run()