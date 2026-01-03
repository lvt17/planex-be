"""
SSE (Server-Sent Events) API endpoints
Provides real-time event streaming to clients
"""
from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.sse_manager import sse_manager
import time
import uuid

bp = Blueprint('sse', __name__)


@bp.route('/events/stream', methods=['GET'])
@jwt_required(optional=True)
def event_stream():
    """
    SSE endpoint for clients to receive real-time updates
    Clients connect to this endpoint and receive events as they happen
    """
    # Get user identity if authenticated
    user_id = get_jwt_identity()
    
    # Generate unique client ID
    client_id = f"{user_id or 'anonymous'}_{uuid.uuid4().hex[:8]}"
    
    # Register client and get their queue
    client_queue = sse_manager.add_client(client_id)
    
    def generate():
        """Generator function that yields SSE messages"""
        try:
            # Send initial connection message
            yield f"data: {{'type': 'connected', 'client_id': '{client_id}'}}\n\n"
            
            # Keep connection alive and send events
            while True:
                try:
                    # Wait for new message with timeout for keep-alive
                    message = client_queue.get(timeout=30)
                    yield message
                except:
                    # Send keep-alive comment every 30 seconds
                    yield f": keep-alive {time.time()}\n\n"
        finally:
            # Clean up when client disconnects
            sse_manager.remove_client(client_id)
    
    # Return SSE response with proper headers
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Connection': 'keep-alive'
        }
    )


@bp.route('/events/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get SSE connection statistics (admin only)"""
    return {
        'connected_clients': sse_manager.get_client_count()
    }
