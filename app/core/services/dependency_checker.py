import logging
from app.core.services.service_container import ServiceContainer

logger = logging.getLogger('app.core.services')

class DependencyChecker:
    """检查系统依赖是否满足"""
    
    REQUIRED_SERVICES = [
        'ai_client_factory',
        'redis_service',
        'correction_service',
        'source_type_manager'
    ]
    
    @classmethod
    def check_required_services(cls):
        """
        检查所有必要服务是否已注册
        
        Returns:
            bool: 所有服务是否可用
        """
        missing_services = []
        
        for service_name in cls.REQUIRED_SERVICES:
            if not ServiceContainer.has(service_name):
                missing_services.append(service_name)
                
        if missing_services:
            logger.warning(f"缺少以下必要服务: {', '.join(missing_services)}")
            return False
            
        logger.info("所有必要服务已注册")
        return True
    
    @classmethod
    def initialize_missing_services(cls):
        """
        初始化缺失的必要服务
        """
        missing_services = []
        
        for service_name in cls.REQUIRED_SERVICES:
            if not ServiceContainer.has(service_name):
                missing_services.append(service_name)
                
        if not missing_services:
            return
            
        logger.info(f"正在初始化缺失的服务: {', '.join(missing_services)}")
        
        # 按照依赖顺序初始化服务
        for service_name in missing_services:
            try:
                if service_name == 'redis_service':
                    from app.core.services.redis_service import RedisService
                    RedisService()
                    logger.info("已初始化 Redis 服务")
                    
                elif service_name == 'ai_client_factory':
                    from app.core.ai import AIClientFactory
                    AIClientFactory()
                    logger.info("已初始化 AI 客户端工厂")
                    
                elif service_name == 'correction_service':
                    from app.core.correction.correction_service import CorrectionService
                    CorrectionService()
                    logger.info("已初始化批改服务")
                    
                elif service_name == 'source_type_manager':
                    from app.core.source_type_manager import SourceTypeManager
                    SourceTypeManager()
                    logger.info("已初始化来源类型管理器")
                    
            except Exception as e:
                logger.error(f"初始化服务 '{service_name}' 失败: {str(e)}")
                continue
    
    @classmethod
    def validate_service_dependencies(cls):
        """
        验证服务之间的依赖关系
        
        Returns:
            bool: 依赖关系是否有效
        """
        # 验证批改服务依赖
        if ServiceContainer.has('correction_service'):
            correction_service = ServiceContainer.get('correction_service')
            if not ServiceContainer.has('ai_client_factory'):
                logger.error("批改服务依赖的AI客户端工厂未注册")
                return False
        
        # 验证AI客户端工厂依赖
        if ServiceContainer.has('ai_client_factory'):
            ai_factory = ServiceContainer.get('ai_client_factory')
            if not ServiceContainer.has('redis_service'):
                logger.error("AI客户端工厂依赖的Redis服务未注册")
                return False
        
        logger.info("服务依赖关系验证通过")
        return True 