#!/usr/bin/env python3
"""
Document Ingestion System for FF_Agent RAG Enhancement
Phase 2: Retrieval Augmented Generation
Handles PDFs, CSVs, JSONs, and text documents for semantic search
"""

import os
import json
import csv
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import hashlib

# For PDF processing (install with: pip install pypdf2)
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: PyPDF2 not installed. PDF support disabled.")

# For enhanced text processing
try:
    import pandas as pd
    PANDAS_SUPPORT = True
except ImportError:
    PANDAS_SUPPORT = False

class DocumentIngester:
    """
    Ingests various document types into vector store for RAG
    Supports: CSV, JSON, TXT, MD, PDF
    """
    
    def __init__(self, vector_store=None):
        """
        Initialize document ingester
        Args:
            vector_store: VectorStore instance for storing embeddings
        """
        self.vector_store = vector_store
        self.ingested_count = 0
        self.failed_count = 0
        self.document_registry = {}  # Track ingested documents
        
        # Document type handlers
        self.handlers = {
            '.csv': self.ingest_csv,
            '.json': self.ingest_json,
            '.txt': self.ingest_text,
            '.md': self.ingest_markdown,
            '.pdf': self.ingest_pdf if PDF_SUPPORT else self.pdf_not_supported,
            '.sql': self.ingest_sql,
            '.py': self.ingest_code
        }
        
        # FibreFlow specific patterns
        self.fibreflow_patterns = {
            'project_codes': r'(LAW|IVY|MAM|MOH|HEIN)[\d-]*',
            'drop_numbers': r'[A-Z]{3}-\d{3,}',
            'pon_references': r'PON[-_]\d+',
            'telecom_terms': [
                'splice loss', 'optical power', 'attenuation',
                'OLT', 'ONU', 'ONT', 'GPON', 'PON',
                'drop', 'pole', 'fibre', 'cable'
            ]
        }
    
    def generate_document_id(self, filepath: str) -> str:
        """Generate unique ID for document"""
        return hashlib.md5(filepath.encode()).hexdigest()[:12]
    
    def extract_metadata(self, filepath: str) -> Dict:
        """Extract metadata from file"""
        path = Path(filepath)
        return {
            'filename': path.name,
            'extension': path.suffix,
            'size_kb': path.stat().st_size / 1024 if path.exists() else 0,
            'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat() if path.exists() else None,
            'ingested_at': datetime.now().isoformat(),
            'document_id': self.generate_document_id(filepath)
        }
    
    def extract_fibreflow_entities(self, text: str) -> Dict:
        """Extract FibreFlow-specific entities from text"""
        entities = {}
        
        # Extract project codes
        project_matches = re.findall(self.fibreflow_patterns['project_codes'], text, re.IGNORECASE)
        if project_matches:
            entities['project_codes'] = list(set(project_matches))
        
        # Extract drop numbers
        drop_matches = re.findall(self.fibreflow_patterns['drop_numbers'], text)
        if drop_matches:
            entities['drop_numbers'] = list(set(drop_matches))[:10]  # Limit to 10
        
        # Extract PON references
        pon_matches = re.findall(self.fibreflow_patterns['pon_references'], text, re.IGNORECASE)
        if pon_matches:
            entities['pon_references'] = list(set(pon_matches))
        
        # Count telecom terms
        term_counts = {}
        for term in self.fibreflow_patterns['telecom_terms']:
            count = len(re.findall(term, text, re.IGNORECASE))
            if count > 0:
                term_counts[term] = count
        if term_counts:
            entities['telecom_terms'] = term_counts
        
        return entities
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks for better context preservation
        """
        chunks = []
        text_length = len(text)
        
        if text_length <= chunk_size:
            return [text]
        
        start = 0
        while start < text_length:
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < text_length:
                # Look for sentence end
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + chunk_size/2:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start with overlap
            start = end - overlap if end < text_length else text_length
        
        return chunks
    
    def ingest_csv(self, filepath: str) -> bool:
        """Ingest CSV file"""
        try:
            metadata = self.extract_metadata(filepath)
            
            if PANDAS_SUPPORT:
                df = pd.read_csv(filepath, nrows=100)  # Sample first 100 rows
                
                # Create searchable description
                doc_text = f"CSV File: {metadata['filename']}\n"
                doc_text += f"Columns: {', '.join(df.columns)}\n"
                doc_text += f"Rows: {len(df)}\n\n"
                
                # Add sample data
                doc_text += "Sample Data:\n"
                doc_text += df.head(5).to_string()
                
                # Detect data patterns
                if 'drop_number' in [col.lower() for col in df.columns]:
                    doc_text += "\n\nNote: This file contains drop data"
                if 'project' in [col.lower() for col in df.columns]:
                    doc_text += "\n\nNote: This file contains project data"
                
            else:
                # Fallback without pandas
                with open(filepath, 'r') as f:
                    reader = csv.reader(f)
                    headers = next(reader)
                    doc_text = f"CSV File: {metadata['filename']}\n"
                    doc_text += f"Columns: {', '.join(headers)}\n"
                    
                    # Read first few rows
                    sample_rows = []
                    for i, row in enumerate(reader):
                        if i >= 5:
                            break
                        sample_rows.append(row)
                    
                    doc_text += f"Sample rows: {len(sample_rows)}\n"
            
            # Extract entities
            entities = self.extract_fibreflow_entities(doc_text)
            metadata['entities'] = entities
            
            # Store in vector database if available
            if self.vector_store:
                self._store_document(
                    document_id=metadata['document_id'],
                    content=doc_text,
                    metadata=metadata,
                    doc_type='csv_schema'
                )
            
            self.ingested_count += 1
            print(f"✅ Ingested CSV: {metadata['filename']}")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest CSV {filepath}: {e}")
            return False
    
    def ingest_json(self, filepath: str) -> bool:
        """Ingest JSON file"""
        try:
            metadata = self.extract_metadata(filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Create searchable description
            doc_text = f"JSON File: {metadata['filename']}\n"
            
            # Handle different JSON structures
            if isinstance(data, dict):
                doc_text += f"Type: Object with {len(data)} keys\n"
                doc_text += f"Keys: {', '.join(list(data.keys())[:20])}\n\n"
                doc_text += "Structure:\n"
                doc_text += json.dumps(data, indent=2)[:1000]  # First 1000 chars
            elif isinstance(data, list):
                doc_text += f"Type: Array with {len(data)} items\n"
                if data and isinstance(data[0], dict):
                    doc_text += f"Item keys: {', '.join(data[0].keys())}\n"
                doc_text += "Sample:\n"
                doc_text += json.dumps(data[:3], indent=2)[:1000]
            
            # Extract entities
            entities = self.extract_fibreflow_entities(doc_text)
            metadata['entities'] = entities
            
            # Check for specific config types
            if 'firebase' in metadata['filename'].lower():
                metadata['config_type'] = 'firebase'
            elif 'settings' in metadata['filename'].lower():
                metadata['config_type'] = 'settings'
            
            # Store in vector database
            if self.vector_store:
                self._store_document(
                    document_id=metadata['document_id'],
                    content=doc_text,
                    metadata=metadata,
                    doc_type='json_config'
                )
            
            self.ingested_count += 1
            print(f"✅ Ingested JSON: {metadata['filename']}")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest JSON {filepath}: {e}")
            return False
    
    def ingest_text(self, filepath: str) -> bool:
        """Ingest text file"""
        try:
            metadata = self.extract_metadata(filepath)
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Extract entities
            entities = self.extract_fibreflow_entities(content)
            metadata['entities'] = entities
            
            # Chunk large documents
            chunks = self.chunk_text(content)
            
            # Store each chunk
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                chunk_metadata['total_chunks'] = len(chunks)
                
                if self.vector_store:
                    self._store_document(
                        document_id=f"{metadata['document_id']}_chunk_{i}",
                        content=chunk,
                        metadata=chunk_metadata,
                        doc_type='text_document'
                    )
            
            self.ingested_count += 1
            print(f"✅ Ingested text: {metadata['filename']} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest text {filepath}: {e}")
            return False
    
    def ingest_markdown(self, filepath: str) -> bool:
        """Ingest markdown file with structure preservation"""
        try:
            metadata = self.extract_metadata(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract headers for structure
            headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
            metadata['headers'] = headers[:10]  # First 10 headers
            
            # Extract code blocks
            code_blocks = re.findall(r'```(\w+)?\n(.*?)```', content, re.DOTALL)
            if code_blocks:
                metadata['has_code'] = True
                metadata['code_languages'] = list(set([lang for lang, _ in code_blocks if lang]))
            
            # Extract entities
            entities = self.extract_fibreflow_entities(content)
            metadata['entities'] = entities
            
            # Check document type
            if 'README' in metadata['filename'].upper():
                metadata['doc_type'] = 'readme'
            elif 'GUIDE' in metadata['filename'].upper():
                metadata['doc_type'] = 'guide'
            elif 'PLAN' in metadata['filename'].upper():
                metadata['doc_type'] = 'plan'
            
            # Chunk and store
            chunks = self.chunk_text(content, chunk_size=1500)  # Larger chunks for markdown
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                
                if self.vector_store:
                    self._store_document(
                        document_id=f"{metadata['document_id']}_chunk_{i}",
                        content=chunk,
                        metadata=chunk_metadata,
                        doc_type='markdown_document'
                    )
            
            self.ingested_count += 1
            print(f"✅ Ingested markdown: {metadata['filename']} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest markdown {filepath}: {e}")
            return False
    
    def ingest_pdf(self, filepath: str) -> bool:
        """Ingest PDF file"""
        if not PDF_SUPPORT:
            return self.pdf_not_supported(filepath)
        
        try:
            metadata = self.extract_metadata(filepath)
            
            # Extract text from PDF
            with open(filepath, 'rb') as f:
                pdf = PdfReader(f)
                text = ""
                for page_num, page in enumerate(pdf.pages):
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page.extract_text()
            
            # Extract entities
            entities = self.extract_fibreflow_entities(text)
            metadata['entities'] = entities
            metadata['page_count'] = len(pdf.pages)
            
            # Chunk and store
            chunks = self.chunk_text(text, chunk_size=1500)
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = i
                
                if self.vector_store:
                    self._store_document(
                        document_id=f"{metadata['document_id']}_chunk_{i}",
                        content=chunk,
                        metadata=chunk_metadata,
                        doc_type='pdf_document'
                    )
            
            self.ingested_count += 1
            print(f"✅ Ingested PDF: {metadata['filename']} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest PDF {filepath}: {e}")
            return False
    
    def pdf_not_supported(self, filepath: str) -> bool:
        """Placeholder when PDF support not available"""
        print(f"⚠️  PDF support not available. Install PyPDF2: pip install PyPDF2")
        return False
    
    def ingest_sql(self, filepath: str) -> bool:
        """Ingest SQL file for query patterns"""
        try:
            metadata = self.extract_metadata(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract table names
            tables = re.findall(r'(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(\w+)', content, re.IGNORECASE)
            metadata['tables_referenced'] = list(set(tables))
            
            # Extract query types
            query_types = []
            if re.search(r'\bSELECT\b', content, re.IGNORECASE):
                query_types.append('SELECT')
            if re.search(r'\bINSERT\b', content, re.IGNORECASE):
                query_types.append('INSERT')
            if re.search(r'\bUPDATE\b', content, re.IGNORECASE):
                query_types.append('UPDATE')
            if re.search(r'\bDELETE\b', content, re.IGNORECASE):
                query_types.append('DELETE')
            metadata['query_types'] = query_types
            
            # Store as query example
            if self.vector_store:
                self._store_document(
                    document_id=metadata['document_id'],
                    content=content,
                    metadata=metadata,
                    doc_type='sql_query'
                )
            
            self.ingested_count += 1
            print(f"✅ Ingested SQL: {metadata['filename']}")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest SQL {filepath}: {e}")
            return False
    
    def ingest_code(self, filepath: str) -> bool:
        """Ingest Python code for API/function reference"""
        try:
            metadata = self.extract_metadata(filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract function/class definitions
            functions = re.findall(r'def\s+(\w+)\s*\(', content)
            classes = re.findall(r'class\s+(\w+)\s*[:\(]', content)
            
            metadata['functions'] = functions[:20]  # First 20 functions
            metadata['classes'] = classes[:10]  # First 10 classes
            
            # Extract imports to understand dependencies
            imports = re.findall(r'(?:from|import)\s+([\w.]+)', content)
            metadata['imports'] = list(set(imports))[:20]
            
            # Create searchable description
            doc_text = f"Python File: {metadata['filename']}\n"
            doc_text += f"Classes: {', '.join(classes)}\n" if classes else ""
            doc_text += f"Functions: {', '.join(functions[:10])}\n" if functions else ""
            doc_text += "\n" + content[:2000]  # First 2000 chars of code
            
            # Store
            if self.vector_store:
                self._store_document(
                    document_id=metadata['document_id'],
                    content=doc_text,
                    metadata=metadata,
                    doc_type='python_code'
                )
            
            self.ingested_count += 1
            print(f"✅ Ingested Python: {metadata['filename']}")
            return True
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Failed to ingest Python {filepath}: {e}")
            return False
    
    def _store_document(self, document_id: str, content: str, metadata: Dict, doc_type: str):
        """Store document in vector database"""
        if not self.vector_store:
            return
        
        try:
            # Generate embedding
            embedding = self.vector_store.generate_embedding(content)
            
            if embedding:
                # Store in vector database
                with self.vector_store.get_connection() as conn:
                    with conn.cursor() as cur:
                        # Check if document already exists
                        cur.execute("""
                            SELECT id FROM schema_embeddings
                            WHERE table_name = %s AND column_name = %s
                        """, (doc_type, document_id))
                        
                        existing = cur.fetchone()
                        
                        if existing:
                            # Update existing
                            cur.execute("""
                                UPDATE schema_embeddings
                                SET description = %s,
                                    embedding = %s::vector,
                                    usage_frequency = usage_frequency + 1
                                WHERE table_name = %s AND column_name = %s
                            """, (content[:2000], embedding, doc_type, document_id))
                        else:
                            # Insert new
                            cur.execute("""
                                INSERT INTO schema_embeddings
                                (table_name, column_name, description, embedding)
                                VALUES (%s, %s, %s, %s::vector)
                            """, (doc_type, document_id, content[:2000], embedding))
                        
                        conn.commit()
                
                # Track in registry
                self.document_registry[document_id] = {
                    'type': doc_type,
                    'metadata': metadata,
                    'ingested_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            print(f"Warning: Could not store embedding: {e}")
    
    def ingest_directory(self, directory_path: str, recursive: bool = True, 
                        file_patterns: List[str] = None) -> Dict:
        """
        Ingest all documents in a directory
        
        Args:
            directory_path: Path to directory
            recursive: Whether to search subdirectories
            file_patterns: List of file patterns to include (e.g., ['*.csv', '*.md'])
        
        Returns:
            Summary of ingestion results
        """
        print(f"\n{'='*60}")
        print(f"Starting document ingestion from: {directory_path}")
        print(f"{'='*60}")
        
        path = Path(directory_path)
        if not path.exists():
            print(f"❌ Directory not found: {directory_path}")
            return {}
        
        # Collect files
        files_to_process = []
        
        if file_patterns:
            for pattern in file_patterns:
                if recursive:
                    files_to_process.extend(path.rglob(pattern))
                else:
                    files_to_process.extend(path.glob(pattern))
        else:
            # Process all supported file types
            for ext, handler in self.handlers.items():
                pattern = f"*{ext}"
                if recursive:
                    files_to_process.extend(path.rglob(pattern))
                else:
                    files_to_process.extend(path.glob(pattern))
        
        # Remove duplicates and filter
        files_to_process = list(set(files_to_process))
        
        # Filter out common unwanted paths
        filtered_files = []
        exclude_dirs = ['node_modules', 'venv', '__pycache__', '.git', 'dist', 'build']
        
        for file in files_to_process:
            if not any(excluded in str(file) for excluded in exclude_dirs):
                filtered_files.append(file)
        
        print(f"Found {len(filtered_files)} files to process")
        
        # Process files
        for file_path in filtered_files:
            ext = file_path.suffix.lower()
            if ext in self.handlers:
                self.handlers[ext](str(file_path))
        
        # Summary
        summary = {
            'total_files': len(filtered_files),
            'ingested': self.ingested_count,
            'failed': self.failed_count,
            'success_rate': (self.ingested_count / len(filtered_files) * 100) if filtered_files else 0,
            'document_types': self._count_document_types()
        }
        
        print(f"\n{'='*60}")
        print(f"Ingestion Complete!")
        print(f"{'='*60}")
        print(f"✅ Successfully ingested: {summary['ingested']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📊 Success rate: {summary['success_rate']:.1f}%")
        print(f"\nDocument types ingested:")
        for doc_type, count in summary['document_types'].items():
            print(f"  - {doc_type}: {count}")
        
        return summary
    
    def _count_document_types(self) -> Dict[str, int]:
        """Count documents by type"""
        type_counts = {}
        for doc_info in self.document_registry.values():
            doc_type = doc_info['type']
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        return type_counts
    
    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search ingested documents
        """
        if not self.vector_store:
            print("No vector store configured")
            return []
        
        # This would use the vector store's search functionality
        # For now, return a placeholder
        return []


# Standalone testing function
def test_ingestion():
    """Test document ingestion with sample files"""
    print("Testing Document Ingestion System")
    
    # Create test ingester (without vector store for testing)
    ingester = DocumentIngester()
    
    # Test with current directory
    summary = ingester.ingest_directory(
        ".",
        recursive=False,
        file_patterns=["*.md", "*.json", "*.csv", "*.py"]
    )
    
    return summary


if __name__ == "__main__":
    # Run test
    test_ingestion()