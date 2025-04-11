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

def create_test_essay():
    """创建测试作文"""
    app = create_app()
    with app.app_context():
        try:
            # 创建测试作文
            essay = Essay(
                title="美丽的春天",
                content="""美丽的春天
春天，一个充满生机与活力的季节，悄然来临。

初春的微风，轻轻抚过大地，唤醒了沉睡一冬的万物。小草从土壤中探出嫩绿的头，树枝上的嫩芽也在悄悄萌发。远远望去，整个大地仿佛披上了一层淡绿色的轻纱，柔和而又充满生命力。

在公园里，早樱和迎春花是春天的先行者。粉嫩的樱花如云似霞，随风轻舞；金黄的迎春花点缀在枝头，宛如繁星点点。花朵们争相绽放，彷使在向世界宣告：春天已经到来！

春雨如丝，轻柔地洒在大地上。这雨水温柔而细腻，滋润着万物生长。雨后的世界更加清新明媚，空气中弥漫着泥土和嫩草的芬芳。小朋友们穿着彩色雨衣，踩着水洼，笑声在雨后的空气中回荡。

春天不仅是视觉的盛宴，更是听觉的享受。清晨，在窗户外可以听到各种鸟儿的欢快鸣叫声，它们有的在枝头歌唱，有的在空中翱翔。这是大自然最美妙的交响乐，每一个音符都充满了生命的活力。

在乡村的田野上，农民们开始了春耕。他们弯着腰，细心地播下希望的种子。油菜花田金黄一片，在阳光下闪闪发光，蜜蜂和蝴蝶在花丛中忙碌地采蜜授粉。这幅生机勃勃的画面，是春天最美的写照。

学校的操场上，孩子们脱下了厚重的冬装，穿着轻便的春装，尽情地奔跑、跳跃。他们的脸上洋溢着灿烂的笑容，宛如春天里最美丽的花朵。老师们组织学生们进行植树活动，让孩子们亲手为大自然增添一抹新绿，也在心中种下爱护环境的种子。

春天是一年四季中最令人期待的季节，它代表着新的开始，带给人们无限的希望和可能。在这个美丽的季节里，我们应该放慢脚步，细细感受春天的气息，让内心也能像春天一样，充满活力和希望。

让我们一起拥抱春天，感受这个季节带给我们的美好与温暖。春天不仅是自然的复苏，也是人们心灵的苏醒，它提醒着我们，生活中总有新的美好等待着我们去发现和珍惜。""",
                status=EssayStatus.PENDING,
                user_id=1,  # 假设用户ID为1
                source_type="text",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.session.add(essay)
            db.session.commit()
            
            logger.info(f"成功创建测试作文 [ID={essay.id}, 标题='{essay.title}']")
            
            return True
            
        except Exception as e:
            logger.error(f"创建测试作文时发生错误: {str(e)}")
            return False

if __name__ == "__main__":
    success = create_test_essay()
    if success:
        logger.info("测试作文创建成功！")
    else:
        logger.error("测试作文创建失败。")
        sys.exit(1) 