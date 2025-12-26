import os
import shutil
import zipfile
import io
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, session, url_for, send_file, abort
from ..models import File, User
from ..init_db import sqlite

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, '../../uploads')  # 所有用户共享的根
os.makedirs(UPLOAD_ROOT, exist_ok=True)

files_bp = Blueprint('files', __name__, template_folder='../templates')

def get_user_folder(user_id):
    """返回用户独立根目录"""
    user_folder = os.path.join(UPLOAD_ROOT, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_folder_tree(base_path, current_rel="", level=0):
    """递归获取文件夹树，用于前端移动操作的树状下拉列表"""
    tree = []
    full_path = os.path.join(base_path, current_rel)
    if not os.path.exists(full_path):
        return []
    try:
        dirs = [d for d in os.listdir(full_path) if os.path.isdir(os.path.join(full_path, d))]
        for d in sorted(dirs):
            rel_path = os.path.join(current_rel, d).replace("\\", "/")
            display_name = "　" * level + "└─ " + d
            tree.append({'path': rel_path, 'display': display_name})
            tree.extend(get_folder_tree(base_path, rel_path, level + 1))
    except PermissionError:
        pass
    return tree

@files_bp.route('/')
@files_bp.route('/<path:folder_path>')
def index(folder_path=''):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user_folder = get_user_folder(user_id)
    files_all = File.query.filter_by(user_id=user_id).all()

    folders = set()
    visible_files = []
    current_folder = folder_path.strip('/')
    prefix = current_folder + '/' if current_folder else ''

    for f in files_all:
        if f.filename.startswith(prefix):
            rest = f.filename[len(prefix):]
            if not rest:
                continue
            if f.is_folder:
                folder_name = rest.split('/')[0]
                folders.add(folder_name)
            else:
                if '/' not in rest:
                    full_path = os.path.join(user_folder, f.filename)
                    f.mtime = datetime.fromtimestamp(os.path.getmtime(full_path)) if os.path.exists(full_path) else None
                    f.size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                    visible_files.append(f)

    folder_tree = get_folder_tree(user_folder)

    folder_infos = []
    for folder in sorted(folders):
        folder_rel = f"{current_folder}/{folder}" if current_folder else folder
        folder_full = os.path.join(user_folder, folder_rel)
        mtime = datetime.fromtimestamp(os.path.getmtime(folder_full)) if os.path.exists(folder_full) else None
        folder_infos.append({'name': folder, 'mtime': mtime})

    return render_template(
        'index.html',
        username=session['username'],
        folder_path=current_folder,
        folders=folder_infos,
        files=visible_files,
        folder_tree=folder_tree
    )

@files_bp.route('/create_folder', methods=['POST'])
def create_folder():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    folder_name = request.form.get('folder_name').strip()
    folder_path = request.form.get('current_path', '').strip('/')
    if not folder_name:
        return redirect(url_for('files.index', folder_path=folder_path))

    user_folder = get_user_folder(session['user_id'])
    full_path = os.path.join(user_folder, folder_path, folder_name)
    os.makedirs(full_path, exist_ok=True)

    db_filename = f"{folder_path}/{folder_name}" if folder_path else folder_name
    if not File.query.filter_by(filename=db_filename, user_id=session['user_id']).first():
        file_record = File(filename=db_filename, user_id=session['user_id'], is_folder=True)
        sqlite.session.add(file_record)
        sqlite.session.commit()
    return redirect(url_for('files.index', folder_path=folder_path))

@files_bp.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    files = request.files.getlist('files')
    folder_path = request.form.get('current_path', '').strip('/')
    user_id = session['user_id']
    user_folder = get_user_folder(user_id)

    for file in files:
        if not file.filename:
            continue
        # 这里确保获取正确属性名
        rel_path = getattr(file, 'webkitRelativePath', file.filename) or file.filename
        rel_path = rel_path.replace("\\", "/")  # 统一分隔符

        save_path = os.path.join(user_folder, folder_path, rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)

        db_filename = f"{folder_path}/{rel_path}" if folder_path else rel_path
        db_filename = db_filename.replace("\\", "/")  # 数据库存相对路径统一

        existing = File.query.filter_by(filename=db_filename, user_id=user_id).first()
        if existing:
            existing.size = os.path.getsize(save_path)
        else:
            parts = db_filename.split('/')
            for i in range(len(parts)-1):
                folder_db_name = '/'.join(parts[:i+1])
                if not File.query.filter_by(filename=folder_db_name, user_id=user_id).first():
                    folder_record = File(filename=folder_db_name, user_id=user_id, is_folder=True)
                    sqlite.session.add(folder_record)
            file_record = File(filename=db_filename, user_id=user_id, size=os.path.getsize(save_path), is_folder=False)
            sqlite.session.add(file_record)

    sqlite.session.commit()
    return redirect(url_for('files.index', folder_path=folder_path))


@files_bp.route('/download/<int:file_id>')
def download(file_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    f = File.query.get(file_id)
    if not f or f.user_id != session['user_id']:
        abort(404)
    user_folder = get_user_folder(f.user_id)
    file_path = os.path.join(user_folder, f.filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_file(file_path, as_attachment=True)

@files_bp.route('/download_folder')
def download_folder():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    folder_path = request.args.get('folder_path', '').strip('/')
    user_folder = get_user_folder(session['user_id'])
    abs_folder_path = os.path.join(user_folder, folder_path)
    if not os.path.exists(abs_folder_path):
        return f"<script>alert('文件夹不存在！');window.history.back();</script>"

    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, filenames in os.walk(abs_folder_path):
            for filename in filenames:
                abs_file = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_file, abs_folder_path)
                zf.write(abs_file, arcname=rel_path)
    memory_file.seek(0)
    zip_name = (folder_path.split('/')[-1] or "root") + ".zip"
    return send_file(memory_file, as_attachment=True, download_name=zip_name)

@files_bp.route('/delete/<file_id>', methods=['POST'])
def delete(file_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    current_path = request.form.get('current_path', '').strip('/')
    user_id = session['user_id']
    user_folder = get_user_folder(user_id)

    if str(file_id).endswith('_folder'):
        folder_name = request.form.get('folder_name')
        rel_folder_path = f"{current_path}/{folder_name}" if current_path else folder_name
        full_folder_path = os.path.join(user_folder, rel_folder_path)

        if os.path.exists(full_folder_path):
            shutil.rmtree(full_folder_path)

        prefix = rel_folder_path + '/'
        affected = File.query.filter(
            File.user_id == user_id,
            (File.filename == rel_folder_path) | (File.filename.startswith(prefix))
        ).all()
        for a in affected:
            sqlite.session.delete(a)
    else:
        f = File.query.get(file_id)
        if f and f.user_id == user_id:
            path = os.path.join(user_folder, f.filename)
            if os.path.exists(path):
                os.remove(path)
            sqlite.session.delete(f)

    sqlite.session.commit()
    return redirect(url_for('files.index', folder_path=current_path))

@files_bp.route('/rename', methods=['POST'])
def rename():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    current_path = request.form.get('current_path', '').strip('/')
    is_folder = request.form.get('is_folder') == '1'
    user_id = session['user_id']
    user_folder = get_user_folder(user_id)

    old_rel = f"{current_path}/{old_name}" if current_path else old_name
    new_rel = f"{current_path}/{new_name}" if current_path else new_name

    old_full = os.path.join(user_folder, old_rel)
    new_full = os.path.join(user_folder, new_rel)

    if not os.path.exists(old_full):
        return "<script>alert('源不存在');window.history.back();</script>"
    if os.path.exists(new_full):
        return "<script>alert('名称已存在');window.history.back();</script>"

    try:
        os.rename(old_full, new_full)
        now = datetime.now().timestamp()
        if is_folder:
            for root, dirs, files in os.walk(new_full):
                os.utime(root, (now, now))
                for f in files:
                    os.utime(os.path.join(root, f), (now, now))
        else:
            os.utime(new_full, (now, now))
    except Exception as e:
        return f"<script>alert('重命名失败: {str(e)}');window.history.back();</script>"

    affected = File.query.filter(File.user_id == user_id, File.filename.startswith(old_rel)).all()
    for f in affected:
        f.filename = f.filename.replace(old_rel, new_rel, 1)
    sqlite.session.commit()

    return redirect(url_for('files.index', folder_path=current_path))

@files_bp.route('/move', methods=['POST'])
def move():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    item_name = request.form.get('item_name')
    is_folder = request.form.get('is_folder') == '1'
    current_path = request.form.get('current_path', '').strip('/')
    target_folder = request.form.get('target_folder', '').strip('/')
    user_id = session['user_id']
    user_folder = get_user_folder(user_id)

    old_rel = f"{current_path}/{item_name}" if current_path else item_name
    new_rel = f"{target_folder}/{item_name}" if target_folder else item_name

    old_full = os.path.join(user_folder, old_rel)
    new_full = os.path.join(user_folder, new_rel)

    if not os.path.exists(old_full):
        return f"<script>alert('源文件不存在！');window.history.back();</script>"
    if os.path.exists(new_full):
        return f"<script>alert('目标位置已存在同名项目！');window.history.back();</script>"

    try:
        shutil.move(old_full, new_full)
        now = datetime.now().timestamp()
        if is_folder:
            for root, dirs, files in os.walk(new_full):
                os.utime(root, (now, now))
                for f in files:
                    os.utime(os.path.join(root, f), (now, now))
        else:
            os.utime(new_full, (now, now))
    except Exception as e:
        return f"<script>alert('移动失败: {str(e)}');window.history.back();</script>"

    affected = File.query.filter(File.user_id == user_id, File.filename.startswith(old_rel)).all()
    for f in affected:
        f.filename = f.filename.replace(old_rel, new_rel, 1)
    sqlite.session.commit()

    return redirect(url_for('files.index', folder_path=current_path))
