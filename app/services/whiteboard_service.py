import json
import uuid
from datetime import datetime
from app.utils.timezone import get_now_vn
from app.extensions import db
from app.models.storage import Storage


class WhiteboardService:
    """Service for whiteboard functionality"""
    
    def __init__(self):
        self.whiteboards = {}  # In-memory storage for whiteboard sessions
    
    def create_whiteboard(self, task_id, user_id, title="Whiteboard Session"):
        """Create a new whiteboard session"""
        whiteboard_id = str(uuid.uuid4())
        
        whiteboard_data = {
            'id': whiteboard_id,
            'task_id': task_id,
            'user_id': user_id,
            'title': title,
            'created_at': get_now_vn().isoformat(),
            'updated_at': get_now_vn().isoformat(),
            'elements': [],
            'connections': [],
            'background': '#ffffff'
        }
        
        self.whiteboards[whiteboard_id] = whiteboard_data
        return whiteboard_data
    
    def get_whiteboard(self, whiteboard_id):
        """Get whiteboard data"""
        return self.whiteboards.get(whiteboard_id)
    
    def update_whiteboard(self, whiteboard_id, elements=None, connections=None, background=None):
        """Update whiteboard data"""
        if whiteboard_id not in self.whiteboards:
            return None
        
        whiteboard = self.whiteboards[whiteboard_id]
        whiteboard['updated_at'] = get_now_vn().isoformat()
        
        if elements is not None:
            whiteboard['elements'] = elements
        if connections is not None:
            whiteboard['connections'] = connections
        if background is not None:
            whiteboard['background'] = background
        
        return whiteboard
    
    def add_element(self, whiteboard_id, element_data):
        """Add an element to the whiteboard"""
        if whiteboard_id not in self.whiteboards:
            return None
        
        whiteboard = self.whiteboards[whiteboard_id]
        element_data['id'] = str(uuid.uuid4())
        element_data['created_at'] = get_now_vn().isoformat()
        
        whiteboard['elements'].append(element_data)
        whiteboard['updated_at'] = get_now_vn().isoformat()
        
        return element_data
    
    def remove_element(self, whiteboard_id, element_id):
        """Remove an element from the whiteboard"""
        if whiteboard_id not in self.whiteboards:
            return False
        
        whiteboard = self.whiteboards[whiteboard_id]
        whiteboard['elements'] = [elem for elem in whiteboard['elements'] if elem['id'] != element_id]
        whiteboard['updated_at'] = get_now_vn().isoformat()
        
        return True
    
    def export_whiteboard_to_image(self, whiteboard_id):
        """Export whiteboard to image format (placeholder implementation)"""
        # This would typically involve rendering the whiteboard elements to an image
        # For now, we'll return a placeholder
        whiteboard = self.whiteboards.get(whiteboard_id)
        if not whiteboard:
            return None
        
        # In a real implementation, this would render the whiteboard to an image
        # and save it to storage
        return {
            'whiteboard_id': whiteboard_id,
            'export_format': 'image',
            'export_time': get_now_vn().isoformat(),
            'url': f'/api/whiteboards/{whiteboard_id}/export'
        }
    
    def get_whiteboards_for_task(self, task_id):
        """Get all whiteboards for a specific task"""
        task_whiteboards = []
        for wb_id, wb_data in self.whiteboards.items():
            if wb_data['task_id'] == task_id:
                task_whiteboards.append(wb_data)
        return task_whiteboards


# Global whiteboard service instance
whiteboard_service = WhiteboardService()
