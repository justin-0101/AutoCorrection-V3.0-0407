"""
WebSocket Manager
Handles WebSocket connections and notifications
"""

import logging
import json
from typing import Dict, Any

# Get logger
logger = logging.getLogger(__name__)

# Store active WebSocket connections
active_connections = {}

def register_connection(user_id, connection):
    """Register a new WebSocket connection
    
    Args:
        user_id: User ID
        connection: WebSocket connection object
    """
    if user_id not in active_connections:
        active_connections[user_id] = []
    
    active_connections[user_id].append(connection)
    logger.info(f"Registered WebSocket connection for user {user_id}")

def unregister_connection(user_id, connection):
    """Unregister a WebSocket connection
    
    Args:
        user_id: User ID
        connection: WebSocket connection object
    """
    if user_id in active_connections:
        if connection in active_connections[user_id]:
            active_connections[user_id].remove(connection)
            logger.info(f"Unregistered WebSocket connection for user {user_id}")
        
        # Clean up empty lists
        if not active_connections[user_id]:
            del active_connections[user_id]

def notify_user(user_id, data: Dict[str, Any]):
    """Send notification to a specific user
    
    Args:
        user_id: User ID
        data: Notification data
    
    Returns:
        bool: Whether the notification was sent
    """
    try:
        if user_id in active_connections and active_connections[user_id]:
            # Serialize data to JSON
            message = json.dumps(data)
            
            # Send to all active connections for this user
            delivered = False
            for connection in active_connections[user_id]:
                try:
                    # In a real implementation, this would actually send to the WebSocket
                    # connection.send(message)
                    
                    # For now, we'll just log
                    logger.info(f"Would send to user {user_id}: {message}")
                    delivered = True
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {str(e)}")
                    # Connection might be dead, unregister it
                    unregister_connection(user_id, connection)
            
            return delivered
        else:
            logger.info(f"No active connections for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {str(e)}")
        return False

def broadcast(data: Dict[str, Any], exclude_users=None):
    """Broadcast message to all connected users
    
    Args:
        data: Notification data
        exclude_users: List of user IDs to exclude
    
    Returns:
        int: Number of users notified
    """
    try:
        exclude_users = exclude_users or []
        
        # Serialize data to JSON
        message = json.dumps(data)
        
        # Track number of users notified
        notified_count = 0
        
        for user_id, connections in list(active_connections.items()):
            # Skip excluded users
            if user_id in exclude_users:
                continue
                
            if connections:
                # Send to all active connections for this user
                for connection in connections:
                    try:
                        # In a real implementation, this would actually send to the WebSocket
                        # connection.send(message)
                        
                        # For now, we'll just log
                        logger.info(f"Would broadcast to user {user_id}: {message}")
                    except Exception as e:
                        logger.error(f"Failed to broadcast message to user {user_id}: {str(e)}")
                        # Connection might be dead, unregister it
                        unregister_connection(user_id, connection)
                
                notified_count += 1
        
        return notified_count
            
    except Exception as e:
        logger.error(f"Failed to broadcast message: {str(e)}")
        return 0 