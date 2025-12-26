from .init_db import sqlite
from datetime import datetime

class User(sqlite.Model):
    __tablename__ = 'user'
    id = sqlite.Column(sqlite.Integer, primary_key=True)
    username = sqlite.Column(sqlite.String(50), unique=True, nullable=False)
    password = sqlite.Column(sqlite.String(128), nullable=False)
    is_admin = sqlite.Column(sqlite.Boolean, default=False)
    created_at = sqlite.Column(sqlite.DateTime, default=datetime.utcnow)
    # 新增字段：最后登录 IP
    last_login_ip = sqlite.Column(sqlite.String(45))  # IPv6 也可存

class File(sqlite.Model):
    __tablename__ = 'file'
    id = sqlite.Column(sqlite.Integer, primary_key=True)
    filename = sqlite.Column(sqlite.String(255), nullable=False)
    user_id = sqlite.Column(sqlite.Integer, nullable=False)
    size = sqlite.Column(sqlite.Integer, default=0)
    is_folder = sqlite.Column(sqlite.Boolean, default=False)
    created_at = sqlite.Column(sqlite.DateTime, default=datetime.utcnow)

