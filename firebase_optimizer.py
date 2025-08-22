#!/usr/bin/env python3
"""
Firebase Query Optimizer for FF_Agent
Provides optimized query methods for different collections
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import firestore
import json

class FirebaseQueryOptimizer:
    """Optimizes Firebase queries based on collection and query type"""
    
    def __init__(self, db):
        self.db = db
        
    def query_meetings(self, question: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Optimized queries for meetings collection"""
        question_lower = question.lower()
        query = self.db.collection('meetings')
        
        # Always order by dateTime for meetings
        query = query.order_by('dateTime', direction=firestore.Query.DESCENDING)
        
        # Check for singular vs plural
        is_singular = any(word in question_lower for word in ['the most recent', 'the latest', 'last meeting', 'most recent meeting', 'latest meeting'])
        
        # Handle specific query patterns
        if is_singular:
            # User wants just ONE meeting
            query = query.limit(1)
            
        elif 'today' in question_lower:
            # Get today's meetings
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            query = query.where('dateTime', '>=', today)
            query = query.where('dateTime', '<', tomorrow)
            query = query.limit(50)
            
        elif 'this week' in question_lower or 'week' in question_lower:
            # Get this week's meetings
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where('dateTime', '>=', start_of_week)
            query = query.limit(100)
            
        elif 'insights' in question_lower:
            # For insights, we want meetings with insights field populated
            # Note: Firestore doesn't support "exists" queries directly
            # So we fetch more and filter in memory
            query = query.limit(200)  # Fetch more to find ones with insights
            
        elif 'recent' in question_lower or 'latest' in question_lower:
            # Get recent meetings (plural)
            # Check how many they want
            if 'last 5' in question_lower or 'five' in question_lower:
                query = query.limit(5)
            elif 'last 10' in question_lower or 'ten' in question_lower:
                query = query.limit(10)
            elif 'last 20' in question_lower or 'twenty' in question_lower:
                query = query.limit(20)
            else:
                query = query.limit(10)  # Default to 10 for "recent"
            
        elif 'action items' in question_lower or 'actions' in question_lower:
            # Meetings with action items
            query = query.limit(100)
            
        else:
            query = query.limit(limit)
        
        # Execute query
        docs = query.stream()
        data = []
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            
            # Parse insights if it's a JSON string
            if 'insights' in doc_data and isinstance(doc_data['insights'], str):
                try:
                    doc_data['insights'] = json.loads(doc_data['insights'])
                except:
                    pass
            
            # Skip meetings without insights if specifically requested
            if 'insights' in question_lower:
                if not doc_data.get('insights'):
                    continue
                    
            # Skip meetings without action items if specifically requested
            if ('action items' in question_lower or 'actions' in question_lower):
                if not doc_data.get('actionItems') or len(doc_data.get('actionItems', [])) == 0:
                    continue
            
            data.append(doc_data)
            
            # Stop early if we have enough filtered results
            if 'insights' in question_lower and len(data) >= 10:
                break
            elif len(data) >= limit:
                break
        
        # Format response based on query type
        if is_singular and data:
            # For single meeting requests, format it nicely
            meeting = data[0]
            formatted = {
                'title': meeting.get('title', 'N/A'),
                'dateTime': meeting.get('dateTime', 'N/A'),
                'organizer': meeting.get('organizer', 'N/A'),
                'duration_minutes': round(meeting.get('duration', 0), 2),
                'summary': meeting.get('summary', ''),
                'participants': meeting.get('participants', []),
                'participants_count': len(meeting.get('participants', [])),
                'action_items': meeting.get('actionItems', []),
                'action_items_count': len(meeting.get('actionItems', [])),
                'meeting_url': meeting.get('meetingUrl', ''),
                'status': meeting.get('status', ''),
                'id': meeting.get('id')
            }
            
            # Add insights if present
            if meeting.get('insights'):
                insights = meeting.get('insights', {})
                if isinstance(insights, dict):
                    formatted['key_insights'] = insights.get('bulletPoints', '')
                else:
                    formatted['key_insights'] = str(insights)
            
            return [formatted]  # Return as single-item list
            
        elif 'insights' in question_lower and data:
            # Return formatted insights data
            formatted_data = []
            for meeting in data[:10]:
                insights = meeting.get('insights', {})
                if isinstance(insights, dict):
                    bullet_points = insights.get('bulletPoints', '')
                else:
                    bullet_points = str(insights)
                    
                formatted_data.append({
                    'title': meeting.get('title', 'N/A'),
                    'dateTime': meeting.get('dateTime', 'N/A'),
                    'organizer': meeting.get('organizer', 'N/A'),
                    'duration_minutes': round(meeting.get('duration', 0), 2),
                    'key_insights': bullet_points[:500] if bullet_points else 'No insights',
                    'summary': meeting.get('summary', '')[:200] if meeting.get('summary') else '',
                    'action_items_count': len(meeting.get('actionItems', [])),
                    'participants_count': len(meeting.get('participants', [])),
                    'meeting_url': meeting.get('meetingUrl', ''),
                    'id': meeting.get('id')
                })
            return formatted_data
            
        elif 'action items' in question_lower or 'actions' in question_lower:
            # Return meetings with action items formatted
            formatted_data = []
            for meeting in data[:20]:
                action_items = meeting.get('actionItems', [])
                formatted_data.append({
                    'title': meeting.get('title', 'N/A'),
                    'dateTime': meeting.get('dateTime', 'N/A'),
                    'organizer': meeting.get('organizer', 'N/A'),
                    'action_items': action_items[:5] if action_items else [],  # First 5 action items
                    'total_actions': len(action_items),
                    'id': meeting.get('id')
                })
            return formatted_data
            
        return data
    
    def query_tasks(self, question: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Optimized queries for tasks collection"""
        question_lower = question.lower()
        query = self.db.collection('tasks')
        
        # Order by appropriate field
        if 'recent' in question_lower or 'latest' in question_lower:
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
        elif 'due' in question_lower or 'deadline' in question_lower:
            query = query.order_by('dueDate', direction=firestore.Query.ASCENDING)
        elif 'priority' in question_lower or 'urgent' in question_lower:
            query = query.order_by('priority', direction=firestore.Query.DESCENDING)
        else:
            query = query.order_by('createdAt', direction=firestore.Query.DESCENDING)
        
        # Add filters based on query
        if 'open' in question_lower or 'pending' in question_lower:
            query = query.where('status', '==', 'open')
        elif 'completed' in question_lower or 'done' in question_lower:
            query = query.where('status', '==', 'completed')
        elif 'overdue' in question_lower:
            query = query.where('dueDate', '<', datetime.now())
            query = query.where('status', '!=', 'completed')
        
        query = query.limit(limit)
        docs = query.stream()
        
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
        
        return data
    
    def query_field_operations(self, collection: str, question: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Optimized queries for field operation collections"""
        question_lower = question.lower()
        query = self.db.collection(collection)
        
        # Try to order by timestamp or date fields
        date_fields = ['timestamp', 'createdAt', 'updatedAt', 'date']
        ordered = False
        
        for field in date_fields:
            try:
                query = query.order_by(field, direction=firestore.Query.DESCENDING)
                ordered = True
                break
            except:
                continue
        
        # Add location-based filters if mentioned
        if 'lawley' in question_lower:
            query = query.where('projectCode', '==', 'LAW001')
        
        query = query.limit(limit)
        docs = query.stream()
        
        data = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
        
        return data
    
    def query_with_pagination(self, collection: str, page_size: int = 20, start_after: Any = None):
        """Query with pagination support"""
        query = self.db.collection(collection).limit(page_size)
        
        if start_after:
            query = query.start_after(start_after)
        
        docs = query.stream()
        data = []
        last_doc = None
        
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            data.append(doc_data)
            last_doc = doc
        
        return {
            'data': data,
            'last_doc': last_doc,
            'has_more': len(data) == page_size
        }