#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Testing the TaskStatus model and related functionality
"""

import unittest
from datetime import datetime, timedelta, UTC

from app import create_app
from app.models.db import db
from app.models.task_status import TaskStatus, TaskState
from app.models.essay import Essay, EssaySourceType
from sqlalchemy import text


class TestTaskStatus(unittest.TestCase):
    """Test the TaskStatus model"""
    
    def setUp(self):
        """Test setup"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test data
        from app.models.user import User
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('password')
        db.session.add(self.user)
        db.session.commit()
        
        # Create sample essays
        self.essay1 = Essay(
            title='Test Essay 1',
            content='This is the content of test essay 1',
            user_id=self.user.id,
            source_type=EssaySourceType.paste.value
        )
        self.essay2 = Essay(
            title='Test Essay 2',
            content='This is the content of test essay 2',
            user_id=self.user.id,
            source_type=EssaySourceType.upload.value
        )
        db.session.add_all([self.essay1, self.essay2])
        db.session.commit()
    
    def tearDown(self):
        """Test cleanup"""
        db.session.close()  # 显式关闭会话
        db.session.remove()
        db.engine.dispose()  # 释放连接池中的所有连接
        db.drop_all()
        self.app_context.pop()
    
    def test_task_status_creation(self):
        """Test creating a task status record"""
        # Create task status
        task_status = TaskStatus(
            task_id='test-task-id-1',
            task_name='process_essay_correction',
            status=TaskState.PENDING,
            related_type='essay',
            related_id=self.essay1.id
        )
        db.session.add(task_status)
        db.session.commit()
        
        # Verify task status was created
        saved_status = TaskStatus.query.filter_by(task_id='test-task-id-1').first()
        self.assertIsNotNone(saved_status)
        self.assertEqual(saved_status.task_name, 'process_essay_correction')
        self.assertEqual(saved_status.status, TaskState.PENDING)
        self.assertEqual(saved_status.related_type, 'essay')
        self.assertEqual(saved_status.related_id, self.essay1.id)
    
    def test_task_status_update(self):
        """Test updating task status"""
        # Create task status
        task_status = TaskStatus(
            task_id='test-task-id-2',
            task_name='process_essay_correction',
            status=TaskState.PENDING,
            related_type='essay',
            related_id=self.essay1.id
        )
        db.session.add(task_status)
        db.session.commit()
        
        # Update status to 'running'
        task_status.status = TaskState.STARTED
        task_status.started_at = datetime.now(UTC)
        db.session.commit()
        
        # Verify update
        updated_status = TaskStatus.query.filter_by(task_id='test-task-id-2').first()
        self.assertEqual(updated_status.status, TaskState.STARTED)
        self.assertIsNotNone(updated_status.started_at)
        
        # Update status to 'success'
        task_status.status = TaskState.SUCCESS
        task_status.completed_at = datetime.now(UTC)
        task_status.result = {'score': 85}
        db.session.commit()
        
        # Verify update
        final_status = TaskStatus.query.filter_by(task_id='test-task-id-2').first()
        self.assertEqual(final_status.status, TaskState.SUCCESS)
        self.assertIsNotNone(final_status.completed_at)
        self.assertEqual(final_status.result['score'], 85)
    
    def test_task_status_query_with_indexes(self):
        """Test query performance with indexes"""
        # Create multiple task statuses
        statuses = []
        for i in range(10):
            status = TaskStatus(
                task_id=f'task-{i}',
                task_name='process_essay_correction',
                status=TaskState.PENDING if i % 3 == 0 else (TaskState.STARTED if i % 3 == 1 else TaskState.SUCCESS),
                related_type='essay',
                related_id=self.essay1.id if i % 2 == 0 else self.essay2.id,
                retry_count=i % 5,
                created_at=datetime.now(UTC) - timedelta(minutes=i)
            )
            statuses.append(status)
        
        db.session.add_all(statuses)
        db.session.commit()
        
        # Test various indexed queries
        # 1. Query by task_id
        task_id_query = TaskStatus.query.filter_by(task_id='task-5').first()
        self.assertIsNotNone(task_id_query)
        self.assertEqual(task_id_query.task_id, 'task-5')
        
        # 2. Query by status
        status_query = TaskStatus.query.filter_by(status=TaskState.PENDING).all()
        self.assertEqual(len(status_query), 4)  # i % 3 == 0 have 4 entries
        
        # 3. Query by task_name
        name_query = TaskStatus.query.filter_by(task_name='process_essay_correction').count()
        self.assertEqual(name_query, 10)  # All tasks have this name
        
        # 4. Query by retry_count
        retry_query = TaskStatus.query.filter_by(retry_count=2).all()
        self.assertEqual(len(retry_query), 2)  # i % 5 == 2 have 2 entries
        
        # 5. Order by created_at
        time_query = TaskStatus.query.order_by(TaskStatus.created_at).all()
        self.assertEqual(time_query[0].task_id, 'task-9')  # Oldest created
        self.assertEqual(time_query[-1].task_id, 'task-0')  # Most recently created
        
        # 6. Query by related_id
        related_query = TaskStatus.query.filter_by(
            related_type='essay', 
            related_id=self.essay1.id
        ).count()
        self.assertEqual(related_query, 5)  # i % 2 == 0 have 5 entries
        
        # 7. Query by status and created_at
        combined_query = TaskStatus.query.filter_by(status=TaskState.SUCCESS).order_by(
            TaskStatus.created_at
        ).all()
        self.assertTrue(all(s.status == TaskState.SUCCESS for s in combined_query))
        self.assertTrue(combined_query[0].created_at <= combined_query[-1].created_at)
    
    def test_task_status_indexes_exist(self):
        """Test that all necessary indexes exist"""
        # Get current database indexes
        with db.engine.connect() as connection:
            result = connection.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type = 'index' AND tbl_name = 'task_statuses'
            """))
            indexes = [row[0] for row in result]
        
        # Verify all necessary indexes exist
        expected_indexes = [
            'ix_task_statuses_task_id',
            'ix_task_statuses_status',
            'ix_task_statuses_task_name',
            'ix_task_statuses_retry_count',
            'ix_task_statuses_created_at',
            'ix_task_statuses_related',
            'ix_task_statuses_status_created_at'
        ]
        
        # Verify all necessary indexes exist
        # SQLite may name indexes differently, so use partial matching
        for expected in expected_indexes:
            matched = False
            for actual in indexes:
                if expected in actual:
                    matched = True
                    break
            self.assertTrue(matched, f"Index {expected} not found")


if __name__ == '__main__':
    unittest.main() 