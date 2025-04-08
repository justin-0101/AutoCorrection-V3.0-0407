#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""测试Essay模型的grade字段"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker

# 使用内存数据库进行测试
engine = create_engine('sqlite:///:memory:')
Base = declarative_base()
Session = sessionmaker(bind=engine)

# 创建简化版Essay模型
class Essay(Base):
    __tablename__ = 'essays'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=False)
    grade = Column(String(50), nullable=True)


class TestEssayGrade(unittest.TestCase):
    """测试Essay模型的grade字段"""
    
    def setUp(self):
        """设置测试环境"""
        Base.metadata.create_all(engine)
        self.session = Session()
    
    def tearDown(self):
        """清理测试环境"""
        self.session.close()
        Base.metadata.drop_all(engine)
    
    def test_create_essay_with_grade(self):
        """测试创建带有grade字段的essay"""
        essay = Essay(
            title="测试作文",
            content="这是一篇测试作文的内容",
            user_id=1,
            grade="高中"
        )
        
        self.session.add(essay)
        self.session.commit()
        
        # 从数据库获取essay
        saved_essay = self.session.query(Essay).first()
        
        self.assertEqual(saved_essay.title, "测试作文")
        self.assertEqual(saved_essay.grade, "高中")
    
    def test_create_essay_without_grade(self):
        """测试创建不带grade字段的essay"""
        essay = Essay(
            title="测试作文",
            content="这是一篇测试作文的内容",
            user_id=1
        )
        
        self.session.add(essay)
        self.session.commit()
        
        # 从数据库获取essay
        saved_essay = self.session.query(Essay).first()
        
        self.assertEqual(saved_essay.title, "测试作文")
        self.assertIsNone(saved_essay.grade)
    
    def test_update_essay_grade(self):
        """测试更新essay的grade字段"""
        # 创建不带grade的essay
        essay = Essay(
            title="测试作文",
            content="这是一篇测试作文的内容",
            user_id=1
        )
        
        self.session.add(essay)
        self.session.commit()
        
        # 更新grade字段
        essay.grade = "初中"
        self.session.commit()
        
        # 从数据库获取更新后的essay
        updated_essay = self.session.query(Essay).first()
        
        self.assertEqual(updated_essay.grade, "初中")


if __name__ == '__main__':
    unittest.main() 