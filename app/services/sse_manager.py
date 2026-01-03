"""
SSE (Server-Sent Events) Manager Service
Handles broadcasting events to all connected clients in real-time
TEMPORARILY DISABLED due to worker timeout issues
"""
import time
import json
from typing import Dict, Set, Any
from flask import Response
import queue
import threading


class SSEManager:
    """Manages SSE connections and event broadcasting"""
    
    def __init__(self):
        # Store active client queues
        self.clients: Dict[str, queue.Queue] = {}
        self.lock = threading.Lock()
        self.enabled = False  # DISABLED - Using Supabase Realtime now
    
    def add_client(self, client_id: str) -> queue.Queue:
        """Register a new SSE client"""
        if not self.enabled:
            return queue.Queue(maxsize=1)  # Dummy queue
            
        with self.lock:
            client_queue = queue.Queue(maxsize=100)
            self.clients[client_id] = client_queue
            print(f"SSE: Client {client_id} connected. Total clients: {len(self.clients)}")
            return client_queue
    
    def remove_client(self, client_id: str):
        """Remove a disconnected SSE client"""
        if not self.enabled:
            return
            
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]
                print(f"SSE: Client {client_id} disconnected. Total clients: {len(self.clients)}")
    
    def broadcast(self, event_type: str, data: Any):
        """Broadcast an event to all connected clients - TEMPORARILY DISABLED"""
        if not self.enabled:
            return  # No-op when disabled
            
        event_data = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        message = f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        
        with self.lock:
            disconnected_clients = []
            for client_id, client_queue in self.clients.items():
                try:
                    # Non-blocking put with timeout
                    client_queue.put_nowait(message)
                except queue.Full:
                    # Queue is full, client is slow - disconnect them
                    disconnected_clients.append(client_id)
                    print(f"SSE: Client {client_id} queue full, disconnecting")
            
            # Clean up disconnected clients
            for client_id in disconnected_clients:
                if client_id in self.clients:
                    del self.clients[client_id]
        
        print(f"SSE: Broadcasted {event_type} to {len(self.clients)} clients")
    
    def send_to_client(self, client_id: str, event_type: str, data: Any):
        """Send an event to a specific client - TEMPORARILY DISABLED"""
        if not self.enabled:
            return
            
        event_data = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        message = f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        
        with self.lock:
            if client_id in self.clients:
                try:
                    self.clients[client_id].put_nowait(message)
                except queue.Full:
                    print(f"SSE: Client {client_id} queue full")
    
    def get_client_count(self) -> int:
        """Get the number of connected clients"""
        with self.lock:
            return len(self.clients)


# Global SSE manager instance
sse_manager = SSEManager()
