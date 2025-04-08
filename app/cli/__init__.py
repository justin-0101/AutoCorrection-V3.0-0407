from flask.cli import AppGroup
from .admin import admin

def init_cli(app):
    """初始化命令行工具"""
    app.cli.add_command(admin) 