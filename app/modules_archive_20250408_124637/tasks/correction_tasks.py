"""
Essay Correction Async Tasks Module
Handle asynchronous tasks related to essay correction
"""
import logging
import json
import time
from datetime import datetime, timedelta
from celery import shared_task
from pathlib import Path
import sys
import traceback

# Ensure working directory is correct
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus
from app.models.db import db
from app.models.user import User
from services.ai_service import AIService
from utils.exceptions import AIServiceError
from utils.websocket_manager import notify_user
from flask import current_app

# Get logger
logger = logging.getLogger(__name__)

@shared_task(
    name='tasks.correction_tasks.process_essay_correction',
    bind=True,
    max_retries=3,
    default_retry_delay=5*60,  # 5 minutes retry delay
    acks_late=True
)
def process_essay_correction(self, essay_id, title, content, user_id=None, grade=None):
    """
    Process essay correction task asynchronously
    
    Args:
        self: Celery task instance
        essay_id: Essay ID
        title: Essay title
        content: Essay content
        user_id: User ID (optional)
        grade: Grade level (optional)
        
    Returns:
        dict: Correction results
    """
    start_time = time.time()
    logger.info(f"Starting async essay correction, ID: {essay_id}")
    
    try:
        # Update essay status to processing
        update_essay_status(essay_id, "processing")
        
        # Create AI service instance
        ai_service = AIService()
        
        # Correct essay
        correction_result = ai_service.correct_essay(
            essay_text=content,
            title=title,
            grade=grade
        )
        
        # Check if correction was successful
        if not correction_result.get('success', False):
            error_msg = f"Essay correction failed: {correction_result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            
            # Update essay status to failed
            update_essay_status(essay_id, "failed", error=error_msg)
            
            # Notify user of task failure
            if user_id:
                notify_user(user_id, {
                    "type": "correction_failed",
                    "essay_id": essay_id,
                    "error": error_msg
                })
                
            return {
                "status": "error",
                "message": "Correction failed, please try again later",
                "error": correction_result.get('error', 'Unknown error'),
                "error_type": correction_result.get('error_type', 'UnknownError')
            }
        
        # Processing time
        processing_time = time.time() - start_time
        
        # Save results to database - ensure this is in app context
        with current_app.app_context():
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                if essay:
                    essay.status = "completed"
                    essay.processed_time = processing_time
                    essay.corrected_text = correction_result.get('corrected_text', '')
                    essay.scores = json.dumps(correction_result.get('score', {}))
                    essay.feedback = json.dumps(correction_result.get('feedback', {}))
                    essay.errors = json.dumps(correction_result.get('errors', []))
                    essay.suggestions = json.dumps(correction_result.get('improvement_suggestions', []))
                    essay.grade = correction_result.get('grade', '')
                    session.commit()
        
        # Notify user of task completion
        result = {
            "status": "success",
            "essay_id": essay_id,
            "title": title,
            "original_text": content,
            "corrected_text": correction_result.get('corrected_text', ''),
            "score": correction_result.get('score', {}),
            "feedback": correction_result.get('feedback', {}),
            "errors": correction_result.get('errors', []),
            "improvement_suggestions": correction_result.get('improvement_suggestions', []),
            "word_count": correction_result.get('word_count', len(content)),
            "processing_time": processing_time,
            "grade": correction_result.get('grade', ''),
            "grade_description": correction_result.get('grade_description', '')
        }
        
        if user_id:
            notify_user(user_id, {
                "type": "correction_completed",
                "essay_id": essay_id,
                "result": result
            })
        
        logger.info(f"Async essay correction completed: ID: {essay_id}, time taken: {processing_time:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"Async essay correction error: ID: {essay_id}: {str(e)}", exc_info=True)
        
        # Record failure and retry within a certain number of attempts
        try:
            # Update essay status to failed
            update_essay_status(essay_id, "failed", error=str(e))
            
            # Notify user of task failure
            if user_id:
                notify_user(user_id, {
                    "type": "correction_failed",
                    "essay_id": essay_id,
                    "error": str(e)
                })
                
            # Try to retry within retry limit
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            # Maximum retry attempts reached
            logger.error(f"Essay correction task reached maximum retry attempts, ID: {essay_id}")
            return {
                "status": "error",
                "message": "Correction task failed multiple times, please contact administrator",
                "error": str(e)
            }

def update_essay_status(essay_id, status, error=None):
    """
    Update essay status
    
    Args:
        essay_id: Essay ID
        status: Status (pending/processing/completed/failed)
        error: Error message (if any)
    """
    try:
        # Ensure we're in an application context
        with current_app.app_context():
            with db.session() as session:
                essay = session.query(Essay).get(essay_id)
                if essay:
                    essay.status = status
                    if error:
                        essay.error_message = error
                    session.commit()
            logger.info(f"Updated essay status to: {status}, ID: {essay_id}")
    except Exception as e:
        logger.error(f"Failed to update essay status, ID: {essay_id}: {str(e)}")

@shared_task(name='tasks.correction_tasks.batch_process_essays')
def batch_process_essays(essay_ids):
    """
    Batch process multiple essays
    
    Args:
        essay_ids: List of essay IDs
        
    Returns:
        list: Processing results or task IDs for each essay
    """
    results = []
    for essay_id in essay_ids:
        try:
            # Ensure we're in an application context
            with current_app.app_context():
                with db.session() as session:
                    essay = session.query(Essay).get(essay_id)
                    if essay and essay.status == "pending":
                        # Start async correction for each essay
                        task = process_essay_correction.delay(
                            essay_id, 
                            essay.title, 
                            essay.content,
                            essay.user_id,
                            essay.grade
                        )
                        results.append({
                            "essay_id": essay_id,
                            "task_id": task.id,
                            "status": "started"
                        })
                        logger.info(f"Started batch correction for essay ID: {essay_id}, task ID: {task.id}")
                    else:
                        results.append({
                            "essay_id": essay_id,
                            "status": "skipped",
                            "reason": f"Essay not found or not in pending status: {essay_id}"
                        })
                        logger.warning(f"Skipped essay in batch processing, ID: {essay_id}")
        except Exception as e:
            logger.error(f"Error starting batch correction for essay ID: {essay_id}: {str(e)}")
            results.append({
                "essay_id": essay_id,
                "status": "error",
                "error": str(e)
            })
    
    return results 
