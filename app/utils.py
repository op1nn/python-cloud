import os
from datetime import datetime

def get_folder_tree(base_path, current_rel="", level=0):
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

def get_file_info(path):
    if not os.path.exists(path):
        return None
    return {
        'size': os.path.getsize(path),
        'mtime': datetime.fromtimestamp(os.path.getmtime(path))
    }
