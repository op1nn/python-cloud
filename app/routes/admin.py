import os
import shutil
import io
import zipfile
from datetime import datetime
from flask import Blueprint, render_template, session, redirect, url_for, request, send_file, abort
from ..models import User, File
from ..init_db import sqlite

admin_bp = Blueprint('admin', __name__, url_prefix='/admin', template_folder='../templates/admin')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, '../../uploads')
os.makedirs(UPLOAD_ROOT, exist_ok=True)



# ------------------ 权限检查 ------------------
@admin_bp.before_request
def check_admin():
    if not session.get('is_admin'):
        return redirect(url_for('auth.login'))

# ------------------ 工具函数 ------------------
def get_abs_path(rel_path: str):
    """返回 uploads 下的绝对路径"""
    return os.path.join(UPLOAD_ROOT, rel_path)

def list_folder(folder_path: str):
    """列出目录下的文件和文件夹信息"""
    abs_path = get_abs_path(folder_path)
    if not os.path.exists(abs_path):
        return []

    items = []
    for entry in sorted(os.listdir(abs_path)):
        full_entry = os.path.join(abs_path, entry)
        items.append({
            'name': entry,
            'is_folder': os.path.isdir(full_entry),
            'mtime': datetime.fromtimestamp(os.path.getmtime(full_entry)),
            'size': os.path.getsize(full_entry) if os.path.isfile(full_entry) else None
        })
    return items

# ------------------ 管理首页 ------------------
@admin_bp.route('/')
def admin_index():
    total_files = File.query.count()
    total_users = len([d for d in os.listdir(UPLOAD_ROOT) if os.path.isdir(os.path.join(UPLOAD_ROOT, d))])
    return render_template('admin.html', total_files=total_files, total_users=total_users)

# ------------------ 浏览 uploads ------------------
def get_user_map():
    """返回 {user_id: username}"""
    users = User.query.all()
    return {str(u.id): u.username for u in users}
# 在工具函数区域添加递归计算大小的函数
def get_dir_size(path):
    """递归计算文件夹总大小"""
    total = 0
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += get_dir_size(entry.path)
    except Exception:
        pass
    return total

# 修改后的 browse_uploads 路由
@admin_bp.route('/uploads')
@admin_bp.route('/uploads/<path:folder_path>')



@admin_bp.route('/uploads')
@admin_bp.route('/uploads/<path:folder_path>')
def browse_uploads(folder_path=''):
    folder_path = folder_path.strip('/')

    users = User.query.all()
    user_map = {str(u.id): u for u in users}  # 保留 User 对象

    # 根目录：显示所有用户
    if folder_path == '':
        items = []
        for entry in sorted(os.listdir(UPLOAD_ROOT)):
            full_entry = os.path.join(UPLOAD_ROOT, entry)
            if os.path.isdir(full_entry):
                user_obj = user_map.get(entry)
                display_name = user_obj.username if user_obj else f"未知用户({entry})"
                last_ip = user_obj.last_login_ip if user_obj and getattr(user_obj, 'last_login_ip', None) else "从未登录"
                items.append({
                    'name': entry,               # 用户文件夹名（ID）
                    'display_name': display_name,
                    'ip_addr': last_ip,          # 这里确保有 ip_addr
                    'is_folder': True,
                    'mtime': datetime.fromtimestamp(os.path.getmtime(full_entry)),
                    'size': get_dir_size(full_entry)
                })
        return render_template('admin_uploads.html', current_path='', items=items)

    # 用户目录或子目录
    abs_path = get_abs_path(folder_path)
    if not os.path.exists(abs_path):
        return f"<script>alert('目录不存在');window.history.back();</script>"

    items = []
    for entry in sorted(os.listdir(abs_path)):
        full_entry = os.path.join(abs_path, entry)
        try:
            stat = os.stat(full_entry)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            size = stat.st_size if os.path.isfile(full_entry) else get_dir_size(full_entry)
        except Exception:
            mtime = datetime.now()
            size = 0

        items.append({
            'name': entry,
            'display_name': entry,
            'is_folder': os.path.isdir(full_entry),
            'mtime': mtime,
            'size': size
        })

    return render_template('admin_uploads.html', current_path=folder_path, items=items)

# ------------------ 下载文件/文件夹 ------------------
@admin_bp.route('/download/<path:rel_path>')
def download(rel_path):
    abs_path = get_abs_path(rel_path)
    if not os.path.exists(abs_path):
        abort(404)

    if os.path.isdir(abs_path):
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(abs_path):
                for f in files:
                    file_path = os.path.join(root, f)
                    arcname = os.path.relpath(file_path, abs_path)
                    zf.write(file_path, arcname=arcname)
        memory_file.seek(0)
        zip_name = os.path.basename(rel_path.rstrip("/")) + ".zip"
        return send_file(memory_file, as_attachment=True, download_name=zip_name)
    else:
        return send_file(abs_path, as_attachment=True)

# ------------------ 删除文件/文件夹 ------------------
@admin_bp.route('/delete', methods=['POST'])
def delete():
    target_path = request.form.get('target_path', '').strip('/')
    abs_path = get_abs_path(target_path)
    if not os.path.exists(abs_path):
        return f"<script>alert('文件/文件夹不存在');window.history.back();</script>"

    is_folder = os.path.isdir(abs_path)
    try:
        if is_folder:
            shutil.rmtree(abs_path)
        else:
            os.remove(abs_path)
    except Exception as e:
        return f"<script>alert('删除失败: {str(e)}');window.history.back();</script>"

    # 删除数据库元数据
    parts = target_path.split('/', 1)
    user_id = int(parts[0])
    prefix = parts[1] if len(parts) > 1 else ""
    affected = File.query.filter(File.user_id == user_id,
                                 (File.filename == prefix) | (File.filename.startswith(prefix + '/'))).all()
    for f in affected:
        sqlite.session.delete(f)
    sqlite.session.commit()

    return redirect(url_for('admin.browse_uploads', folder_path=os.path.dirname(target_path)))

# ------------------ 重命名文件/文件夹 ------------------
@admin_bp.route('/rename', methods=['POST'])
def rename():
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '').strip('/')

    old_full = get_abs_path(os.path.join(current_path, old_name))
    new_full = get_abs_path(os.path.join(current_path, new_name))

    if not os.path.exists(old_full):
        return "<script>alert('源不存在');window.history.back();</script>"
    if os.path.exists(new_full):
        return "<script>alert('目标已存在');window.history.back();</script>"

    try:
        os.rename(old_full, new_full)
    except Exception as e:
        return f"<script>alert('重命名失败: {str(e)}');window.history.back();</script>"

    # 更新数据库
    parts = (current_path + '/' + old_name).split('/', 1)
    user_id = int(parts[0])
    old_rel = parts[1] if len(parts) > 1 else old_name
    new_rel = new_name if not parts[1:] else parts[1].replace(old_name, new_name, 1)

    affected = File.query.filter(File.user_id == user_id,
                                 File.filename.startswith(old_rel)).all()
    for f in affected:
        f.filename = f.filename.replace(old_rel, new_rel, 1)
    sqlite.session.commit()

    return redirect(url_for('admin.browse_uploads', folder_path=current_path))

@admin_bp.route('/api/stats')
def get_stats():
    total_files = File.query.count()
    # 返回当前时间戳和文件总数
    return {
        "time": datetime.now().strftime('%H:%M'),
        "count": total_files
    }

