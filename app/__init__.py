#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建Flask应用实例

Args:
    config_name: 配置名称，默认为'default'
    
Returns:
    Flask应用实例
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import click
from pathlib import Path
from flask_socketio import SocketIO

# 加载配置和配置类
from app.config import load_config, Config
from app.extensions import db, login_manager, migrate, init_extensions

# 加载模型
from app.models.user import User
from app.models.essay import Essay
from app.models.correction import Correction
from app.models.payment import Payment
from app.models.membership import MembershipPlan

# 加载路由
from app.routes.main_routes import main_bp
from app.routes.admin_routes import admin_bp
from app.api.v1.auth import auth_bp
from app.api.v1.correction import correction_bp
from app.api.v1.membership import membership_bp
from app.api.v1.admin import admin_api_bp
from app.api.v1.example import example_bp, register_example_blueprint
from app.api.v1.essays import essays_bp
from app.api.v1 import api_v1_bp  # 导入主API v1蓝图

# 加载环境变量
def load_env_vars():
    """加载环境变量"""
    # 加载根目录下的.env文件
    root_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    app_dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    
    # 加载应用程序目录下的.env文件
    if os.path.exists(root_dotenv_path):
        load_dotenv(root_dotenv_path)
        print(f"加载根目录下的.env文件成功: {root_dotenv_path}")
    # 如果根目录下的.env文件不存在，则加载应用程序目录下的.env
    elif os.path.exists(app_dotenv_path):
        load_dotenv(app_dotenv_path)
        print(f"加载应用程序目录下的.env文件成功: {app_dotenv_path}")
    else:
        print(f"警告: 没有找到.env文件，请检查: {root_dotenv_path}, {app_dotenv_path}")

# 设置日志
def setup_logging(app):
    """设置日志"""
    # 加载日志目录
    log_dir = os.environ.get('LOG_DIR', 'logs')
    
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    
    # 设置日志文件
    file_handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=1024 * 1024 * 10, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    
    # 设置控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    console_handler.setLevel(logging.INFO)
    
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 添加Flask日志记录器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)
    
    # 设置Flask应用程序的日志级别
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    return app

# 加载项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

# 创建SocketIO实例
socketio = SocketIO()

def initialize_services(app):
    """初始化服务层（依赖数据库）"""
    try:
        # 1. 初始化服务容器
        from app.core.services.service_container import ServiceContainer
        ServiceContainer.initialize()
        
        # 1.1 初始化新的依赖注入容器
        try:
            from app.core.services.service_registry_di import ServiceContainer as DIContainer
            DIContainer.init_app(app)
            app.logger.info("依赖注入容器已初始化")
        except Exception as di_error:
            app.logger.warning(f"依赖注入容器初始化失败: {str(di_error)}")
        
        # 2. 启用模拟模式（测试环境）
        if app.config.get('TESTING'):
            ServiceContainer.enable_mock_mode()
            
        # 3. 检查并初始化缺失的服务
        from app.core.services.dependency_checker import DependencyChecker
        if not DependencyChecker.check_required_services():
            app.logger.warning("检查并初始化缺失的服务失败，将尝试初始化所有服务..")
            DependencyChecker.initialize_missing_services()
            
        # 4. 验证服务依赖关系
        if not DependencyChecker.validate_service_dependencies():
            raise RuntimeError("服务依赖关系验证失败")
            
        # 5. 检查所有服务的状态
        from app.core.services.health_checker import HealthChecker
        health_status = HealthChecker.check_all_services()
        for service_name, status in health_status.items():
            if status['status'] == 'unhealthy':
                app.logger.warning(f"服务 '{service_name}' 状态异常，请检查: {status}")
                
        app.logger.info("所有服务已初始化")
        return True
    except Exception as e:
        app.logger.error(f"初始化服务层时出错: {str(e)}")
        raise

def create_app(config_name='default'):
    """
    创建Flask应用实例
    
    Args:
        config_name: 配置名称，默认为'default'
        
    Returns:
        Flask应用实例
    """
    # 加载环境变量
    load_env_vars()
    
    # 确保猴子补丁已应用
    try:
        from app.patch import apply_patches
        apply_patches()
        print("所有猴子补丁应用完成")
    except Exception as e:
        logging.warning(f"应用猴子补丁时出错: {str(e)}")
    
    # 明确设置模板文件夹位置
    template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
    
    # 创建应用实例，明确指定模板目录
    app = Flask(__name__, 
                template_folder=template_dir,  # 明确指定使用app/templates目录
                instance_relative_config=True)
    
    print(f"应用已创建，使用配置: {config_name}")
    print(f"模板文件夹路径: {app.template_folder}")
    
    app.config.from_object(load_config(config_name))
    
    # 创建必要的目录
    create_directories(app)
    
    # 确保数据库目录存在
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_dir = os.path.join(base_dir, 'instance')
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # 确保数据库文件存在
    db_path = os.path.join(db_dir, 'essay_correction.db')
    if not os.path.exists(db_path):
        open(db_path, 'a').close()
    
    # 修改数据库URI为绝对路径
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.replace("\\", "/")}'
    
    # 初始化扩展
    init_extensions(app)
    
    # 初始化服务
    from app.core.services.init_services import ensure_services
    if not ensure_services():
        app.logger.error("服务初始化失败")
        # 不要在这里抛出异常，让应用继续启动
    
    # 注册蓝图
    register_blueprints(app, main_bp, admin_bp, api_v1_bp)
    
    # 注册示例API蓝图
    register_example_blueprint(app)
    app.logger.info("示例API蓝图已注册")
    app.logger.info("蓝图已注册")
    
    # 注册错误处理器
    register_error_handlers(app)
    app.logger.info("错误处理器已注册")
    
    # 注册命令
    register_commands(app)
    app.logger.info("命令已注册")
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    app.logger.info("SocketIO已初始化")
    
    # 初始化源类型管理器
    from app.core.source_type_manager import init_source_types
    init_source_types()
    app.logger.info("源类型管理器已初始化")
    
    # 设置监控
    from app.core.monitoring import setup_monitoring
    setup_monitoring(app)
    app.logger.info("监控设置已初始化")
    
    # 导入和注册监控API
    try:
        from app.api.v1.monitoring import init_app as init_monitoring
        init_monitoring(app)
        app.logger.info("监控API已注册")
    except Exception as e:
        app.logger.warning(f"注册监控API时出错: {str(e)}")
    
    app.logger.info("应用已初始化")
    
    return app

def register_error_handlers(app):
    """注册错误处理和命令"""
    @app.errorhandler(404)
    def page_not_found(e):
        """404页面未找到"""
        from flask import render_template, jsonify, request
        if request.is_json:
            return jsonify({"error": "Not Found", "message": "页面未找到"}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        """500内部服务器错误"""
        from flask import render_template, jsonify, request
        app.logger.error(f"系统错误: {str(e)}")
        if request.is_json:
            return jsonify({"error": "Internal Server Error", "message": "系统错误"}), 500
        return render_template('errors/500.html'), 500
        
    @app.errorhandler(401)
    def unauthorized(e):
        """401未授权"""
        from flask import render_template, jsonify, request
        if request.is_json:
            return jsonify({"error": "Unauthorized", "message": "未授权"}), 401
        return render_template('errors/401.html'), 401
        
    @app.errorhandler(403)
    def forbidden(e):
        """403禁止访问"""
        from flask import render_template, jsonify, request
        if request.is_json:
            return jsonify({"error": "Forbidden", "message": "禁止访问"}), 403
        return render_template('errors/403.html'), 403
    
    # 注册全局错误处理器
    try:
        from app.core.api.error_handler import error_handler
        error_handler.init_app(app)
        app.logger.info("全局错误处理器已初始化")
    except Exception as e:
        app.logger.error(f"注册全局错误处理器时出错: {str(e)}")

def register_commands(app):
    """注册命令"""
    @app.cli.command('init-db')
    def init_db():
        """初始化数据库"""
        from app.models.db import db
        db.create_all()
        click.echo('数据库表已创建')
        
        # 创建默认角色和用户
        create_default_roles_and_users() # type: ignore
        
        click.echo('所有扩展（包括数据库）已初始化')
    
    @app.cli.command('create-admin')
    @click.argument('username')
    @click.argument('password')
    @click.argument('email')
    def create_admin(username, password, email):
        """创建管理员用户"""
        from app.models.user import User, Role
        from app.models.db import db
        
        # 检查管理员角色是否存在
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='管理员')
            db.session.add(admin_role)
        
        user = User.query.filter_by(username=username).first()
        if user:
            click.echo(f'用户 {username} 已存在')
            return
        
        # 创建管理员用户
        user = User(
            username=username,
            email=email,
            is_active=True
        )
        user.set_password(password)
        user.roles.append(admin_role)
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'管理员 {username} 已创建成功!')
        
    @app.cli.command('check-model-fields')
    def check_model_fields():
        """检查所有模型字段是否符合命名规范"""
        from app.core.db.model_migration import check_all_models, generate_migration_plan
        
        click.echo('检查所有模型字段是否符合命名规范..')
        issues = check_all_models()
        
        if not issues:
            click.echo('所有模型字段均符合命名规范')
            return
            
        # 统计总问题数
        total_issues = sum(len(info['issues']) for info in issues.values())
        click.echo(f'发现 {len(issues)} 个模型，共存在 {total_issues} 个字段命名问题')
        
        # 输出问题详情
        click.echo('\n输出问题详情')
        click.echo(generate_migration_plan())
        
    @app.cli.command('generate-field-migration')
    @click.option('--output', '-o', default='migrations/field_migration.py',
                  help='输出迁移文件')
    def generate_field_migration(output):
        """生成字段迁移文件"""
        from app.core.db.model_migration import generate_migration_plan
        import os
        
        # 创建输出目录
        os.makedirs(os.path.dirname(output), exist_ok=True)
        
        # 生成迁移文件
        plan = generate_migration_plan()
        
        # 保存文件
        with open(output, 'w', encoding='utf-8') as f:
            f.write(plan)
            
        click.echo(f'字段迁移文件已生成到 {output}')
        
    @app.cli.command('apply-field-migration')
    @click.option('--dry-run', is_flag=True, default=True,
                  help='仅检查，不实际应用')
    def apply_field_migration(dry_run):
        """应用字段迁移"""
        from app.core.db.model_migration import scan_models, apply_field_renames
        from app.core.db import session_manager
        
        if dry_run:
            click.echo('仅检查，不实际应用')
        
        # 获取所有模型
        models = scan_models()
        click.echo(f'发现 {len(models)} 个模型')
        
        total_renamed = 0
        renamed_models = 0
        
        # 遍历所有模型
        for model in models:
            renames = apply_field_renames(model, dry_run=dry_run)
            if renames:
                renamed_models += 1
                total_renamed += len(renames)
                
                # 输出重命名详情
                click.echo(f'字段重命名 {model.__name__} 发现 {len(renames)} 个字段重命名')
                for old, new in renames.items():
                    click.echo(f'  - {old} -> {new}')
        
        # 提交事务
        if not dry_run and total_renamed > 0:
            session_manager.commit()
            
        # 输出结果
        if total_renamed > 0:
            click.echo(f'共发现 {renamed_models} 个模型，共重命名 {total_renamed} 个字段')
            if not dry_run:
                click.echo('请检查并提交事务')
        else:
            click.echo('没有发现需要重命名的字段')
            
    @app.cli.command('check-model-relationships')
    @click.option('--model', '-m', help='需要检查的模型')
    def check_model_relationships(model):
        """检查所有模型关系是否符合规范"""
        from app.core.db.relationship_manager import check_relationships
        from app.core.db.model_migration import scan_models
        
        # 获取所有模型
        models = scan_models()
        click.echo(f'发现 {len(models)} 个模型')
        
        # 如果指定了模型，则只检查该模型
        if model:
            models = [m for m in models if m.__name__ == model]
            if not models:
                click.echo(f'没有找到模型 {model}')
                return
        
        total_issues = 0
        models_with_issues = 0
        
        # 遍历所有模型，检查关系
        for model_class in models:
            issues = check_relationships(model_class)
            if issues:
                models_with_issues += 1
                total_issues += len(issues)
                
                # 输出问题详情
                click.echo(f'模型 {model_class.__name__} 存在 {len(issues)} 个关系问题')
                for issue in issues:
                    click.echo(f'  - {issue["relation"]}: {issue["message"]}')
                    click.echo(f'    当前关系: {issue["current"]}')
                    click.echo(f'    推荐关系: {issue["recommended"]}')
        
        # 输出结果
        if total_issues > 0:
            click.echo(f'共发现 {models_with_issues} 个模型，共存在 {total_issues} 个关系问题')
        else:
            click.echo('所有模型关系均符合规范')
            
    @app.cli.command('analyze-model-relationships')
    @click.option('--model', '-m', help='需要分析的模型')
    @click.option('--output', '-o', default='docs/model_relationships.md',
                  help='输出迁移文件')
    def analyze_model_relationships(model, output):
        """分析模型关系，生成关系分析报告"""
        from app.core.db.relationship_manager import analyze_model_relationships
        from app.core.db.model_migration import scan_models
        import os
        
        # 获取所有模型
        models = scan_models()
        click.echo(f'发现 {len(models)} 个模型')
        
        # 如果指定了模型，则只分析该模型
        if model:
            models = [m for m in models if m.__name__ == model]
            if not models:
                click.echo(f'没有找到模型 {model}')
                return
        
        # 生成关系分析结果
        results = []
        for model_class in models:
            results.append(analyze_model_relationships(model_class))
        
        # 生成Markdown文件
        lines = ["# 模型关系分析", ""]
        
        for result in results:
            model_name = result['model']
            lines.append(f"## {model_name}")
            lines.append("")
            
            # 添加模型基本信息
            lines.append(f"- **模型名**: {result['table']}")
            lines.append(f"- **关系数**: {len(result['relationships'])}")
            lines.append(f"- **问题数**: {len(result['issues'])}")
            lines.append("")
            
            # 添加关系详情
            if result['relationships']:
                lines.append("### 关系详情")
                lines.append("")
                lines.append("| 模型字段 | 关系类型 | 目标模型 | 懒加载 | 级联删除 | 反向引用 |")
                lines.append("| --- | --- | --- | --- | --- | --- |")
                
                for rel in result['relationships']:
                    rel_name = rel['name']
                    rel_type = rel['type']
                    target = rel['target']
                    lazy = rel['lazy']
                    cascade = rel['cascade']
                    backref = rel['backref'] or rel['back_populates'] or '-'
                    
                    lines.append(f"| {rel_name} | {rel_type} | {target} | {lazy} | {cascade} | {backref} |")
                
                lines.append("")
            
            # 添加问题详情
            if result['issues']:
                lines.append("### 问题详情")
                lines.append("")
                
                for issue in result['issues']:
                    lines.append(f"- **{issue['relation']}**: {issue['message']}")
                    lines.append(f"  - 当前关系 `{issue['current']}`")
                    lines.append(f"  - 推荐关系 `{issue['recommended']}`")
                
                lines.append("")
        
        # 保存文件
        os.makedirs(os.path.dirname(output), exist_ok=True)
        
        # 保存文件
        with open(output, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            
        click.echo(f'模型关系分析报告已生成到 {output}')

    # 注册API检查命令
    @app.cli.command('api-check')
    def api_check():
        """检查所有API蓝图并生成权限报告"""
        from flask import current_app
        
        click.echo("检查所有API蓝图并生成权限报告..")
        
        # 获取所有API蓝图
        api_blueprints = []
        for blueprint_name, blueprint in current_app.blueprints.items():
            if 'api' in blueprint_name.lower():
                api_blueprints.append(blueprint)
        
        click.echo(f"发现 {len(api_blueprints)} 个API蓝图:")
        for bp in api_blueprints:
            click.echo(f" - {bp.name} (URL路径: {bp.url_prefix})")
        
        # 检查所有权限
        click.echo("\n检查所有权限..")
        permission_routes = []
        for rule in current_app.url_map.iter_rules():
            view_func = current_app.view_functions[rule.endpoint]
            
            # 检查是否有权限要求
            if hasattr(view_func, '_requires_permission'):
                permission = getattr(view_func, '_requires_permission')
                permission_routes.append((rule, permission))
            elif hasattr(view_func, '_requires_role'):
                role = getattr(view_func, '_requires_role')
                permission_routes.append((rule, f"角色限制: {role}"))
        
        if permission_routes:
            for rule, permission in permission_routes:
                click.echo(f" - {rule} (权限限制: {permission})")
        else:
            click.echo(" 没有发现权限限制的API蓝图")
            
        click.echo("\n所有API已检查完毕")

def configure_logging(app):
    """
    设置日志
    
    Args:
        app: Flask应用实例
    """
    # 创建日志目录
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        try:
            os.mkdir(log_dir)
        except OSError as e:
            app.logger.error(f"无法创建日志目录 {log_dir}: {e}")
            # 如果目录创建失败，则不尝试文件日志
            return 

    # 设置控制台日志 (always enabled)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO) # Set root level based on debug
    # Clear existing handlers to avoid duplicates if reconfiguring
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # 添加Flask日志记录器
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    app.logger.info('所有扩展（包括数据库）已初始化')

def register_blueprints(app, *blueprints):
    """
    注册蓝图

    Args:
        app: Flask应用实例
        blueprints: 需要注册的蓝图列表  # <--- 添加新参数
    """
    for blueprint in blueprints:          # <--- 遍历所有蓝图
        app.register_blueprint(blueprint) # <--- 注册蓝图
        



def create_directories(app):
    """
    创建应用实例所需的所有目录
    
    Args:
        app: Flask应用实例
    """
    # 创建上传目录
    uploads_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
    
    # 创建临时目录
    temp_dir = os.path.join(app.root_path, 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    # 创建日志目录
    log_dir = os.path.join(app.root_path, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        app.logger.info(f"日志目录已创建: {log_dir}")
