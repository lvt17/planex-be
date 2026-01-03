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
    SSE endpoint - DISABLED - Migrated to Supabase Realtime
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return response
    
    return jsonify({
        'error': 'SSE has been migrated to Supabase Realtime for better stability',
        'status': 'migrated'
    }), 410  # Gone


@bp.route('/events/stats', methods=['GET'])
def get_stats():
    """Get SSE connection statistics"""
    return jsonify({
        'connected_clients': sse_manager.get_client_count()
    })
