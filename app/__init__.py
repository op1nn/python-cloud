from flask import Flask
from .config import Config
from .init_db import sqlite

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB
    sqlite.init_app(app)

    # ⚠️ 只在 app_context 下导入一次模型
    with app.app_context():
        from . import models  # 导入模型，保证 create_all 可以识别
        sqlite.create_all()

    # 注册蓝图
    from .routes.auth import auth_bp
    from .routes.file_ops import files_bp
    from .routes.folder_ops import folder_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(folder_bp)
    app.register_blueprint(admin_bp)

    return app
