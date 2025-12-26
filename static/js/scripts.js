// 1. 上传逻辑
function autoSubmitUpload() {
    const form = document.getElementById('uploadForm');
    const formData = new FormData(form);
    const xhr = new XMLHttpRequest();
    const wrapper = document.getElementById('uploadProgressWrapper');
    const bar = document.getElementById('uploadProgressBar');
    const percentText = document.getElementById('progressPercent');
    const statusText = document.getElementById('progressStatus');

    wrapper.style.display = 'block';
    xhr.upload.addEventListener('progress', e => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            bar.style.width = percent + '%';
            percentText.innerText = percent + '%';
            statusText.innerText = '正在上传...';
        }
    });

    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4) {
            if (xhr.status === 200 || xhr.status === 204) {
                statusText.innerText = '成功！刷新中...';
                setTimeout(() => location.reload(), 500);
            } else {
                alert('上传出错');
                wrapper.style.display = 'none';
            }
        }
    };
    xhr.open('POST', form.action, true);
    xhr.send(formData);
}

// 2. 弹窗触发
function openCreateModal() {
    new bootstrap.Modal(document.getElementById('createModal')).show();
}

function openRenameModal(oldName, isFolder) {
    document.getElementById('renameOldName').value = oldName;
    document.getElementById('renameNewName').value = oldName;
    document.getElementById('renameIsFolder').value = isFolder;
    new bootstrap.Modal(document.getElementById('renameModal')).show();
}

// 移动模态框监听器
document.addEventListener('DOMContentLoaded', () => {
    const moveModalEl = document.getElementById('moveModal');
    if(moveModalEl){
        moveModalEl.addEventListener('show.bs.modal', e => {
            const btn = e.relatedTarget;
            document.getElementById('moveItemName').value = btn.getAttribute('data-item');
            document.getElementById('moveIsFolder').value = btn.getAttribute('data-isfolder');
        });
    }
});

// 3. 排序逻辑
let currentSort = { col: null, asc: true };
function sortTable(colIndex) {
    const table = document.getElementById('fileTable');
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.rows);
    const headerCells = table.tHead.rows[0].cells;

    if (currentSort.col === colIndex) currentSort.asc = !currentSort.asc;
    else { currentSort.col = colIndex; currentSort.asc = true; }

    const folders = rows.filter(r => r.querySelector('.folder-color'));
    const files = rows.filter(r => !r.querySelector('.folder-color'));

    const compare = (a, b) => {
        let valA, valB;
        if(colIndex === 1) { // 大小列用 data-size 排序
            valA = parseFloat(a.cells[1].getAttribute('data-size')) || 0;
            valB = parseFloat(b.cells[1].getAttribute('data-size')) || 0;
        } else {
            valA = a.cells[colIndex].innerText.trim().toLowerCase();
            valB = b.cells[colIndex].innerText.trim().toLowerCase();
        }
        if (valA === valB) return 0;
        return currentSort.asc ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
    }

    folders.sort(compare);
    files.sort(compare);

    tbody.innerHTML = '';
    folders.concat(files).forEach(r => tbody.appendChild(r));

    // 更新图标
    Array.from(headerCells).forEach((cell, idx) => {
        const icon = cell.querySelector('.sort-icon');
        if (icon) {
            if (idx === colIndex) {
                icon.className = currentSort.asc ? 'bi bi-sort-down sort-icon' : 'bi bi-sort-up sort-icon';
                icon.style.color = '#4361ee';
            } else {
                icon.className = 'bi bi-arrow-down-up sort-icon';
                icon.style.color = '#ccc';
            }
        }
    });
}