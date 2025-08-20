import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from sqlalchemy import create_engine, text
from langchain_openai import ChatOpenAI
from langchain.agents import create_sql_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd

load_dotenv()


class FF_Agent:
    """FF_Agent - AI Database Query Agent for Neon and Firebase"""
    
    def __init__(self):
        self.agent_name = "FF_Agent"
        self.llm = ChatOpenAI(
            temperature=float(os.getenv("TEMPERATURE", 0.1)),
            model="gpt-4o-mini"
        )
        self.neon_db = self._init_neon()
        self.firebase_db = self._init_firebase()
        self.sql_agent = self._init_sql_agent()
        self.context = []
        self.max_context_length = 10
        
    def _init_neon(self) -> SQLDatabase:
        """Initialize Neon PostgreSQL connection"""
        database_url = os.getenv("NEON_DATABASE_URL")
        if not database_url:
            raise ValueError("NEON_DATABASE_URL not set")
        
        engine = create_engine(database_url)
        return SQLDatabase(engine)
    
    def _init_firebase(self) -> firestore.Client:
        """Initialize Firebase connection"""
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not cred_path:
            raise ValueError("FIREBASE_CREDENTIALS_PATH not set")
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    
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
    
    def query_neon(self, question: str) -> Dict[str, Any]:
        """Query Neon database using natural language"""
        try:
            result = self.sql_agent.invoke({"input": question})
            return {
                "success": True,
                "data": result.get("output"),
                "source": "neon",
                "agent": self.agent_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "neon",
                "agent": self.agent_name
            }
    
    def query_firebase(self, collection: str, question: str) -> Dict[str, Any]:
        """Query Firebase using natural language"""
        try:
            firebase_prompt = PromptTemplate(
                input_variables=["question", "collection"],
                template="""
                Convert this question to Firebase Firestore query parameters:
                Question: {question}
                Collection: {collection}
                
                Return a JSON with:
                - field: the field to query
                - operator: (==, <, >, <=, >=, array-contains, in)
                - value: the value to compare
                - limit: number of results (optional)
                - order_by: field to order by (optional)
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=firebase_prompt)
            query_params = chain.run(question=question, collection=collection)
            
            collection_ref = self.firebase_db.collection(collection)
            docs = collection_ref.stream()
            
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
                "agent": self.agent_name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "source": "firebase",
                "agent": self.agent_name
            }
    
    def query(self, question: str, source: str = "auto") -> Dict[str, Any]:
        """Main query interface"""
        if source == "auto":
            context_prompt = PromptTemplate(
                input_variables=["question"],
                template="""
                Determine if this question should be answered using:
                1. "neon" - for structured/relational data queries
                2. "firebase" - for document/NoSQL queries
                
                Question: {question}
                
                Return only "neon" or "firebase"
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=context_prompt)
            source = chain.run(question=question).strip().lower()
        
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
            If not specified, return "default"
            
            Question: {question}
            
            Return only the collection name.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=extract_prompt)
        return chain.run(question=question).strip()
    
    def add_context(self, query: str, result: Dict[str, Any]):
        """Maintain conversation context"""
        self.context.append({
            "query": query,
            "result": result
        })
        if len(self.context) > self.max_context_length:
            self.context.pop(0)
    
    def query_with_context(self, question: str) -> Dict[str, Any]:
        """Query with conversation context"""
        context_str = "\n".join([
            f"Previous: {c['query']} -> {c['result'].get('data', 'Error')}"
            for c in self.context[-3:]
        ])
        
        enhanced_question = f"""
        Context: {context_str}
        Current Question: {question}
        """
        
        result = self.query(enhanced_question)
        self.add_context(question, result)
        return result
    
    def validate_sql(self, sql: str) -> bool:
        """Validate SQL query for safety"""
        dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
        sql_upper = sql.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        return True
    
    def execute_raw_sql(self, query: str) -> pd.DataFrame:
        """Execute raw SQL on Neon database with validation"""
        if not self.validate_sql(query):
            raise ValueError("Dangerous SQL operation detected")
        
        with self.neon_db._engine.connect() as conn:
            result = conn.execute(text(query))
            return pd.DataFrame(result.fetchall(), columns=result.keys())