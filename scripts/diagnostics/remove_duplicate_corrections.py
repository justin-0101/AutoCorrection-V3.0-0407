#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import argparse
from datetime import datetime
from sqlalchemy import func

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models.essay import Essay
from app.models.correction import Correction

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='检测并删除重复的批改记录')
    parser.add_argument('--mode', type=str, choices=['interactive', 'auto'], default='auto',
                      help='运行模式: interactive(交互式) 或 auto(自动)')
    parser.add_argument('--strategy', type=str, choices=['earliest', 'latest', 'skip'], default='latest',
                      help='自动模式下的策略: earliest(保留最早), latest(保留最新), skip(跳过)')
    parser.add_argument('--specific-essay', type=int, help='只处理指定ID的作文')
    parser.add_argument('--specific-correction', type=int, help='自动模式下保留指定ID的批改记录')
    
    return parser.parse_args()

def remove_duplicate_corrections(args):
    """检测并删除重复的批改记录"""
    app = create_app()
    with app.app_context():
        try:
            # 查询每个作文ID对应的批改记录数量
            if args.specific_essay:
                # 如果指定了作文ID，只检查该作文
                correction_count = db.session.query(func.count(Correction.id)).filter(
                    Correction.essay_id == args.specific_essay
                ).scalar()
                
                essays_with_multiple_corrections = [args.specific_essay] if correction_count > 1 else []
                logger.info(f"检查指定的作文ID: {args.specific_essay}, 批改记录数: {correction_count}")
            else:
                # 查询所有有多个批改记录的作文
                essay_correction_counts = db.session.query(
                    Correction.essay_id, 
                    func.count(Correction.id).label('count')
                ).group_by(Correction.essay_id).all()
                
                # 找出有多个批改记录的作文
                essays_with_multiple_corrections = [
                    item[0] for item in essay_correction_counts if item[1] > 1
                ]
            
            if not essays_with_multiple_corrections:
                logger.info("没有找到具有重复批改记录的作文，无需处理")
                return
            
            logger.info(f"发现 {len(essays_with_multiple_corrections)} 个作文具有多个批改记录")
            
            total_duplicates_removed = 0
            
            for essay_id in essays_with_multiple_corrections:
                # 获取该作文的所有批改记录
                corrections = db.session.query(Correction).filter(
                    Correction.essay_id == essay_id
                ).order_by(Correction.created_at).all()
                
                logger.info(f"作文ID: {essay_id} 有 {len(corrections)} 条批改记录")
                
                # 获取作文信息
                essay = db.session.query(Essay).filter(Essay.id == essay_id).first()
                essay_title = essay.title if essay else f"未找到 (ID: {essay_id})"
                
                # 打印每条批改记录的信息
                for i, correction in enumerate(corrections, 1):
                    logger.info(f"  记录 #{i}: ID={correction.id}, 状态={correction.status}, 创建时间={correction.created_at}, 更新时间={correction.updated_at}")
                
                # 要保留的记录
                record_to_keep = None
                
                if args.mode == 'interactive':
                    # 交互模式
                    print(f"\n作文 '{essay_title}' (ID: {essay_id}) 有 {len(corrections)} 条批改记录")
                    print("选项:")
                    print("1. 保留最早创建的记录")
                    print("2. 保留最新创建的记录")
                    print("3. 保留指定ID的记录")
                    print("4. 跳过此作文")
                    
                    choice = input("请选择操作 (1-4): ").strip()
                    
                    if choice == "4":
                        logger.info(f"跳过处理作文ID: {essay_id}")
                        continue
                    
                    if choice == "1":
                        # 保留最早创建的记录
                        record_to_keep = min(corrections, key=lambda x: x.created_at)
                        logger.info(f"保留最早创建的记录: ID={record_to_keep.id}")
                    
                    elif choice == "2":
                        # 保留最新创建的记录
                        record_to_keep = max(corrections, key=lambda x: x.created_at)
                        logger.info(f"保留最新创建的记录: ID={record_to_keep.id}")
                    
                    elif choice == "3":
                        # 保留指定ID的记录
                        while True:
                            try:
                                record_id = int(input(f"请输入要保留的记录ID (可选: {', '.join([str(c.id) for c in corrections])}): "))
                                record_to_keep = next((c for c in corrections if c.id == record_id), None)
                                
                                if record_to_keep:
                                    logger.info(f"保留指定ID的记录: ID={record_to_keep.id}")
                                    break
                                else:
                                    print(f"错误: 未找到ID为 {record_id} 的记录，请重新输入")
                            except ValueError:
                                print("错误: 请输入有效的数字ID")
                
                else:
                    # 自动模式
                    if args.specific_correction:
                        # 如果指定了批改记录ID，保留该记录
                        record_to_keep = next((c for c in corrections if c.id == args.specific_correction), None)
                        if record_to_keep:
                            logger.info(f"保留指定ID的记录: ID={record_to_keep.id}")
                        else:
                            logger.warning(f"未找到指定ID的记录: {args.specific_correction}，将使用默认策略")
                    
                    if args.strategy == 'skip' and not record_to_keep:
                        logger.info(f"跳过处理作文ID: {essay_id}")
                        continue
                    
                    if not record_to_keep:
                        if args.strategy == 'earliest':
                            # 保留最早创建的记录
                            record_to_keep = min(corrections, key=lambda x: x.created_at)
                            logger.info(f"保留最早创建的记录: ID={record_to_keep.id}")
                        else:  # 默认使用latest策略
                            # 保留最新创建的记录
                            record_to_keep = max(corrections, key=lambda x: x.created_at)
                            logger.info(f"保留最新创建的记录: ID={record_to_keep.id}")
                
                # 删除其他记录
                if record_to_keep:
                    records_to_delete = [c for c in corrections if c.id != record_to_keep.id]
                    
                    for record in records_to_delete:
                        logger.info(f"删除批改记录: ID={record.id}")
                        db.session.delete(record)
                    
                    total_duplicates_removed += len(records_to_delete)
                    db.session.commit()
                    logger.info(f"已删除 {len(records_to_delete)} 条重复记录，保留记录 ID={record_to_keep.id}")
            
            logger.info(f"总共删除了 {total_duplicates_removed} 条重复批改记录")
            
        except Exception as e:
            logger.error(f"处理重复批改记录时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()

if __name__ == "__main__":
    args = parse_args()
    remove_duplicate_corrections(args) 