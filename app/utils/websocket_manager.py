#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WebSocket Manager Utility
Handles sending notifications via WebSocket.
"""

import logging
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# 初始化SocketIO
socketio = SocketIO()

def notify_user(user_id: int, event: str, data: dict):
    """Send notification to a user via WebSocket."""
    try:
        socketio.emit(event, data, room=f'user_{user_id}')
        logger.info(f"[WebSocket] Notified user {user_id} about event '{event}' with data: {data}")
    except Exception as e:
        logger.error(f"[WebSocket] Failed to notify user {user_id}: {e}") 