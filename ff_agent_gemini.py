import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from sqlalchemy import create_engine, text, inspect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import json
import redis
from datetime import datetime

load_dotenv()


class FF_Agent_Gemini:
    """FF_Agent with Gemini - AI Database Query Agent for FibreFlow"""
    
    def __init__(self):
        self.agent_name = "FF_Agent_Gemini"
        self.llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            temperature=float(os.getenv("TEMPERATURE", 0.1)),
            google_api_key=os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        )
        
        print("Initializing Neon connection...")
        self.neon_db = self._init_neon()
        
        print("Initializing Firebase connection...")
        self.firebase_db = self._init_firebase()
        
        print("Creating SQL agent...")
        self.sql_agent = self._init_sql_agent()
        
        self.context = []
        self.max_context_length = 10
        
        # Initialize Redis cache if available
        self.cache = self._init_cache()
        
    def _init_neon(self) -> SQLDatabase:
        """Initialize Neon PostgreSQL connection"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not set")
        
        engine = create_engine(database_url)
        
        # Test connection
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("✓ Neon database connected successfully")
        except Exception as e:
            print(f"✗ Neon connection failed: {e}")
            raise
        
        return SQLDatabase(engine)
    
    def _init_firebase(self) -> Optional[firestore.Client]:
        """Initialize Firebase connection"""
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not cred_path or not os.path.exists(cred_path):
            print("⚠ Firebase credentials not found - Firebase queries disabled")
            return None
        
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            client = firestore.client()
            print("✓ Firebase connected successfully")
            return client
        except Exception as e:
            print(f"⚠ Firebase connection failed: {e}")
            return None
    
    def _init_sql_agent(self):
        """Create SQL agent for Neon database"""
        toolkit = SQLDatabaseToolkit(
            db=self.neon_db,
            llm=self.llm
        )
        
        return create_sql_agent(
            llm=self.llm,
            toolkit=toolkit,
            verbose=True,
            agent_type="openai-tools",
            max_iterations=5,
            early_stopping_method="force",
            handle_parsing_errors=True
        )
    
    def _init_cache(self) -> Optional[redis.Redis]:
        """Initialize Redis cache if available"""
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True
            )
            r.ping()
            print("✓ Redis cache connected")
            return r
        except:
            print("⚠ Redis not available - caching disabled")
            return None
    
    def get_database_schema(self) -> Dict[str, List[str]]:
        """Get Neon database schema information"""
        inspector = inspect(self.neon_db._engine)
        schema = {}
        
        for table_name in inspector.get_table_names():
            columns = []
            for col in inspector.get_columns(table_name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"])
                })
            schema[table_name] = columns
        
        return schema
    
    def query_neon(self, question: str) -> Dict[str, Any]:
        """Query Neon database using natural language"""
        
        # Check cache
        if self.cache:
            cache_key = f"neon:{question}"
            cached = self.cache.get(cache_key)
            if cached:
                return json.loads(cached)
        
        try:
            # Enhanced prompt with schema context
            schema_info = self.get_database_schema()
            enhanced_question = f"""
            Database Schema: {json.dumps(schema_info, indent=2)}
            
            Question: {question}
            
            Generate and execute the appropriate SQL query.
            """
            
            result = self.sql_agent.invoke({"input": enhanced_question})
            
            response = {
                "success": True,
                "data": result.get("output"),
                "source": "neon",
                "agent": self.agent_name,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache result
            if self.cache:
                self.cache.setex(cache_key, 300, json.dumps(response))
            
            return response
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "neon",
                "agent": self.agent_name
            }
    
    def query_firebase(self, collection: str, question: str) -> Dict[str, Any]:
        """Query Firebase using natural language"""
        if not self.firebase_db:
            return {
                "success": False,
                "error": "Firebase not configured",
                "source": "firebase",
                "agent": self.agent_name
            }
        
        try:
            firebase_prompt = PromptTemplate(
                input_variables=["question", "collection"],
                template="""
                Convert this question to Firebase Firestore query:
                Question: {question}
                Collection: {collection}
                
                Generate Python code that:
                1. Queries the collection
                2. Filters based on the question
                3. Returns relevant documents
                
                Return only the query logic, not the full code.
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=firebase_prompt)
            query_logic = chain.run(question=question, collection=collection)
            
            # For now, return all documents - you can enhance this with actual query execution
            collection_ref = self.firebase_db.collection(collection)
            docs = collection_ref.limit(100).stream()
            
            results = []
            for doc in docs:
                results.append({
                    "id": doc.id,
                    "data": doc.to_dict()
                })
            
            return {
                "success": True,
                "data": results,
                "source": "firebase",
                "collection": collection,
                "agent": self.agent_name,
                "query_logic": query_logic
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "firebase",
                "agent": self.agent_name
            }
    
    def query(self, question: str, source: str = "auto") -> Dict[str, Any]:
        """Main query interface with FibreFlow context"""
        
        # Add FibreFlow context
        fibreflow_context = """
        This is FibreFlow system data. Tables likely include:
        - Users/Customers
        - Orders
        - Products/Inventory
        - Subscriptions
        - Transactions
        """
        
        if source == "auto":
            context_prompt = PromptTemplate(
                input_variables=["question", "context"],
                template="""
                Given this FibreFlow context: {context}
                
                Determine if this question should be answered using:
                1. "neon" - for structured/relational data (PostgreSQL)
                2. "firebase" - for document/NoSQL data
                
                Question: {question}
                
                Return only "neon" or "firebase"
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=context_prompt)
            source = chain.run(question=question, context=fibreflow_context).strip().lower()
        
        if source == "neon":
            return self.query_neon(question)
        elif source == "firebase":
            collection = self._extract_collection(question)
            return self.query_firebase(collection, question)
        else:
            return {
                "success": False,
                "error": f"Unknown source: {source}",
                "agent": self.agent_name
            }
    
    def _extract_collection(self, question: str) -> str:
        """Extract Firebase collection name from question"""
        extract_prompt = PromptTemplate(
            input_variables=["question"],
            template="""
            Extract the Firebase collection name from this question.
            Common FibreFlow collections: users, orders, products, inventory, subscriptions
            
            Question: {question}
            
            Return only the collection name.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=extract_prompt)
        return chain.run(question=question).strip()
    
    def execute_raw_sql(self, query: str) -> pd.DataFrame:
        """Execute raw SQL on Neon database with validation"""
        if not self.validate_sql(query):
            raise ValueError("Dangerous SQL operation detected")
        
        with self.neon_db._engine.connect() as conn:
            result = conn.execute(text(query))
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    
    def validate_sql(self, sql: str) -> bool:
        """Validate SQL query for safety"""
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        sql_upper = sql.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        return True
    
    def query_with_context(self, question: str) -> Dict[str, Any]:
        """Query with conversation context"""
        context_str = "\n".join([
            f"Previous: {c['query']} -> {c['result'].get('data', 'Error')}"
            for c in self.context[-3:]
        ])
        
        if context_str:
            enhanced_question = f"""
            Previous context: {context_str}
            Current question: {question}
            """
        else:
            enhanced_question = question
        
        result = self.query(enhanced_question)
        
        # Add to context
        self.context.append({
            "query": question,
            "result": result
        })
        if len(self.context) > self.max_context_length:
            self.context.pop(0)
        
        return result