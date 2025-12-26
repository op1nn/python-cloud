from flask import Blueprint, request, session, redirect, url_for
from ..init_db import sqlite
from ..models import File  # 从 models 导入 File
from .. import sqlite
from ..config import Config
import os

folder_bp = Blueprint('folder', __name__)

@folder_bp.route('/create_folder', methods=['POST'])
def create_folder():
    if 'user_id' not in session: return redirect(url_for('auth.login'))
    folder_name = request.form.get('folder_name').strip()
    folder_path = request.form.get('current_path', '').strip('/')
    if not folder_name: return redirect(url_for('file.index', folder_path=folder_path))

    full_path = os.path.join(Config.UPLOAD_FOLDER, folder_path, folder_name)
    os.makedirs(full_path, exist_ok=True)

    db_filename = f"{folder_path}/{folder_name}" if folder_path else folder_name
    if not File.query.filter_by(filename=db_filename, user_id=session['user_id']).first():
        file_record = File(filename=db_filename, user_id=session['user_id'], is_folder=True)
        sqlite.session.add(file_record)
        sqlite.session.commit()
    return redirect(url_for('file.index', folder_path=folder_path))
