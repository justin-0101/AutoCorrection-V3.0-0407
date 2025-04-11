#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app import create_app, db
from app.models.essay import Essay, EssayStatus
from app.models.correction import Correction, CorrectionStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_status_inconsistency():
    """修复作文和批改记录之间的状态不一致问题"""
    app = create_app()
    with app.app_context():
        try:
            # 步骤1: 找出所有状态不一致的记录
            inconsistent_records = []
            corrections = db.session.query(Correction).all()
            logger.info("=== 检查批改记录和作文状态一致性 ===")
            
            for correction in corrections:
                essay = db.session.query(Essay).filter(Essay.id == correction.essay_id).first()
                if not essay:
                    logger.error(f"批改记录ID {correction.id} 关联的作文ID {correction.essay_id} 不存在")
                    continue
                
                if essay.status != correction.status:
                    inconsistent_records.append((essay, correction))
                    logger.warning(f"不一致: 作文ID {essay.id} 状态为 {essay.status}，但批改记录ID {correction.id} 状态为 {correction.status}")
            
            logger.info(f"发现 {len(inconsistent_records)} 个状态不一致的记录")
            
            if not inconsistent_records:
                logger.info("没有需要修复的不一致记录，程序退出")
                return
            
            # 步骤2: 提示用户选择修复方式
            print("\n状态不一致修复选项:")
            print("1. 将批改记录状态同步为与作文状态一致")
            print("2. 将作文状态同步为与批改记录状态一致")
            print("3. 智能修复(根据实际情况选择最合适的状态)")
            print("4. 退出不做修改")
            
            choice = input("请选择修复方式 (1-4): ").strip()
            
            if choice == "4":
                logger.info("用户选择不修复，程序退出")
                return
            
            fixed_count = 0
            
            if choice == "1":
                # 将批改记录状态同步为与作文状态一致
                logger.info("将批改记录状态同步为与作文状态一致...")
                for essay, correction in inconsistent_records:
                    old_status = correction.status
                    correction.status = essay.status
                    logger.info(f"批改记录ID {correction.id} 状态从 {old_status} 更新为 {correction.status}")
                    fixed_count += 1
                    
                db.session.commit()
                
            elif choice == "2":
                # 将作文状态同步为与批改记录状态一致
                logger.info("将作文状态同步为与批改记录状态一致...")
                for essay, correction in inconsistent_records:
                    old_status = essay.status
                    essay.status = correction.status
                    logger.info(f"作文ID {essay.id} 状态从 {old_status} 更新为 {essay.status}")
                    fixed_count += 1
                    
                db.session.commit()
                
            elif choice == "3":
                # 智能修复
                logger.info("执行智能修复...")
                for essay, correction in inconsistent_records:
                    # 优先级: COMPLETED > CORRECTING > PENDING > FAILED
                    if essay.status == EssayStatus.COMPLETED.value or correction.status == CorrectionStatus.COMPLETED.value:
                        # 如果任一状态为COMPLETED，将两者都设为COMPLETED
                        old_essay_status = essay.status
                        old_correction_status = correction.status
                        essay.status = EssayStatus.COMPLETED.value
                        correction.status = CorrectionStatus.COMPLETED.value
                        logger.info(f"修复完成: 作文ID {essay.id} 状态从 {old_essay_status} 更新为 {essay.status}, "
                                    f"批改记录ID {correction.id} 状态从 {old_correction_status} 更新为 {correction.status}")
                    
                    elif essay.status == EssayStatus.CORRECTING.value or correction.status == CorrectionStatus.CORRECTING.value:
                        # 如果任一状态为CORRECTING，将两者都设为CORRECTING
                        old_essay_status = essay.status
                        old_correction_status = correction.status
                        essay.status = EssayStatus.CORRECTING.value
                        correction.status = CorrectionStatus.CORRECTING.value
                        logger.info(f"修复中: 作文ID {essay.id} 状态从 {old_essay_status} 更新为 {essay.status}, "
                                    f"批改记录ID {correction.id} 状态从 {old_correction_status} 更新为 {correction.status}")
                    
                    elif essay.status == EssayStatus.PENDING.value or correction.status == CorrectionStatus.PENDING.value:
                        # 如果任一状态为PENDING，将两者都设为PENDING
                        old_essay_status = essay.status
                        old_correction_status = correction.status
                        essay.status = EssayStatus.PENDING.value
                        correction.status = CorrectionStatus.PENDING.value
                        logger.info(f"等待处理: 作文ID {essay.id} 状态从 {old_essay_status} 更新为 {essay.status}, "
                                    f"批改记录ID {correction.id} 状态从 {old_correction_status} 更新为 {correction.status}")
                    
                    elif essay.status == EssayStatus.FAILED.value or correction.status == CorrectionStatus.FAILED.value:
                        # 如果任一状态为FAILED，将两者都设为FAILED
                        old_essay_status = essay.status
                        old_correction_status = correction.status
                        essay.status = EssayStatus.FAILED.value
                        correction.status = CorrectionStatus.FAILED.value
                        logger.info(f"处理失败: 作文ID {essay.id} 状态从 {old_essay_status} 更新为 {essay.status}, "
                                    f"批改记录ID {correction.id} 状态从 {old_correction_status} 更新为 {correction.status}")
                    
                    fixed_count += 1
                    
                db.session.commit()
            
            logger.info(f"成功修复 {fixed_count} 个状态不一致的记录")
            
            # 再次检查是否还有不一致
            remaining_inconsistent = 0
            for correction in db.session.query(Correction).all():
                essay = db.session.query(Essay).filter(Essay.id == correction.essay_id).first()
                if essay and essay.status != correction.status:
                    remaining_inconsistent += 1
            
            if remaining_inconsistent > 0:
                logger.warning(f"仍有 {remaining_inconsistent} 个状态不一致的记录")
            else:
                logger.info("所有状态不一致的记录已修复")
            
        except Exception as e:
            logger.error(f"修复状态不一致时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()

if __name__ == "__main__":
    fix_status_inconsistency() 