"""
SSE (Server-Sent Events) API endpoints
Provides real-time event streaming to clients
"""
from flask import Blueprint, request, Response, jsonify
from flask_jwt_extended import decode_token
from app.services.sse_manager import sse_manager
import time
import uuid

bp = Blueprint('sse', __name__)


@bp.route('/events/stream', methods=['GET', 'OPTIONS'])
def event_stream():
    """
    SSE endpoint for clients to receive real-time updates
    Clients connect to this endpoint and receive events as they happen
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    # Get user identity from token in query params or header
    user_id = None
    try:
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if token:
            decoded = decode_token(token)
            user_id = decoded.get('sub')
    except:
        pass  # Anonymous connection is OK
    
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
    response = Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        }
    )
    return response


@bp.route('/events/stats', methods=['GET'])
def get_stats():
    """Get SSE connection statistics"""
    return jsonify({
        'connected_clients': sse_manager.get_client_count()
    })
