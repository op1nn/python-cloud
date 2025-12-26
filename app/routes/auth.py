from flask import Blueprint, render_template, request, redirect, session, url_for
from .. import sqlite
from ..models import User

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


# --- 工具函数：获取客户端真实 IP (挪到路由外面) ---
def get_client_ip():
    if 'X-Real-IP' in request.headers:
        return request.headers['X-Real-IP']
    if 'X-Forwarded-For' in request.headers:
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr


# --- 登录路由 ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if not user or user.password != password:
            return render_template('login.html', msg='用户名或密码错误')

        # 登录成功，写入 session
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin

        # ------------------- 更新最后登录 IP (使用刚才定义的工具函数) -------------------
        user.last_login_ip = get_client_ip()
        sqlite.session.commit()

        return redirect(url_for('files.index'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return render_template('register.html', msg='用户名或密码不能为空')
        if User.query.filter_by(username=username).first():
            return render_template('register.html', msg='用户名已存在')

        user = User(username=username, password=password)
        sqlite.session.add(user)
        sqlite.session.commit()

        # 第一个用户设为管理员
        if user.id == 1:
            user.is_admin = True
            sqlite.session.commit()

        return redirect(url_for('auth.login'))
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))