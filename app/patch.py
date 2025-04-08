# -*- coding: utf-8 -*-
"""
补丁文件
测试文件修改权限 - 2025-04-08
猴子补丁模块 - 在应用启动前修复'User' object has no attribute 'roles'错误
"""

import logging

logger = logging.getLogger(__name__)

def apply_patches():
    """
    应用所有猴子补丁
    """
    # 导入User模型，避免循环导入
    from app.models.user import User
    
    # 定义通用的roles属性访问方法
    def get_roles(self):
        """返回用户角色列表"""
        try:
            return [ur.role for ur in self.user_roles]
        except Exception as e:
            logger.warning(f"访问用户角色时出错: {str(e)}")
            return []
    
    # 检查User类是否已经有roles属性
    if not hasattr(User, 'roles'):
        # 添加roles属性到User类
        User.roles = property(get_roles)
        logger.info("成功应用User.roles猴子补丁")
    
    logger.info("所有猴子补丁应用完成")
    return True 