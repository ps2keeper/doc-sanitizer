const API = '/api/sensitive-words';
let selectedFile = null;
let autoSaveTimer = null;

// --- 敏感词管理 ---

async function loadWords() {
    const resp = await fetch(API);
    const words = await resp.json();
    const tbody = document.getElementById('wordsTable');
    tbody.innerHTML = '';
    if (words.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center">暂无敏感词配置</td></tr>';
    } else {
        words.forEach(w => {
            const tr = document.createElement('tr');

            // 启用/禁用复选框
            const tdCheck = document.createElement('td');
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'form-check-input';
            checkbox.checked = w.enabled === 1;
            checkbox.title = w.enabled ? '已启用' : '已禁用';
            checkbox.addEventListener('change', () => toggleWord(w.id, checkbox.checked));
            tdCheck.appendChild(checkbox);

            const tdWord = document.createElement('td');
            const inputWord = document.createElement('input');
            inputWord.className = 'form-control form-control-sm';
            inputWord.value = w.word;
            inputWord.addEventListener('change', () => updateWord(w.id, inputWord, inputReplacement));
            tdWord.appendChild(inputWord);

            const tdRepl = document.createElement('td');
            const inputReplacement = document.createElement('input');
            inputReplacement.className = 'form-control form-control-sm';
            inputReplacement.value = w.replacement;
            inputReplacement.addEventListener('change', () => updateWord(w.id, inputWord, inputReplacement));
            tdRepl.appendChild(inputReplacement);

            const tdDel = document.createElement('td');
            const btnDel = document.createElement('button');
            btnDel.className = 'btn btn-sm btn-danger';
            btnDel.textContent = '×';
            btnDel.addEventListener('click', () => deleteWord(w.id));
            tdDel.appendChild(btnDel);

            tr.appendChild(tdCheck);
            tr.appendChild(tdWord);
            tr.appendChild(tdRepl);
            tr.appendChild(tdDel);
            tbody.appendChild(tr);
        });
    }
    updateProcessButton();
}

async function toggleWord(id, enabled) {
    await fetch(`${API}/${id}/toggle`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({enabled})
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function addWord() {
    const word = document.getElementById('newWord').value.trim();
    const replacement = document.getElementById('newReplacement').value.trim();
    if (!word || !replacement) return alert('请填写敏感词和替换词');

    await fetch(API, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word, replacement})
    });
    document.getElementById('newWord').value = '';
    document.getElementById('newReplacement').value = '';
    await loadWords();
}

async function updateWord(id, wordInput, replacementInput) {
    await fetch(`${API}/${id}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({word: wordInput.value, replacement: replacementInput.value})
    });
}

async function deleteWord(id) {
    await fetch(`${API}/${id}`, {method: 'DELETE'});
    await loadWords();
}

async function saveWords() {
    // Export current words as JSON and re-import (sync mechanism via export)
    const resp = await fetch(`${API}/export`);
    const data = await resp.json();
    const statusEl = document.getElementById('saveStatus');
    statusEl.textContent = '💾 已保存 ' + formatTime(new Date());
    statusEl.className = 'text-success me-2';
    statusEl.style.fontSize = '0.8rem';
}

async function exportWords() {
    const resp = await fetch(`${API}/export`);
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '敏感词配置.json';
    a.click();
    URL.revokeObjectURL(url);
}

function importWords() {
    document.getElementById('importInput').click();
}

async function handleImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    const data = JSON.parse(text);
    const resp = await fetch(`${API}/import`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    const result = await resp.json();
    if (result.error) {
        alert('导入失败：' + result.error);
    } else {
        alert(`成功导入 ${result.imported} 条`);
    }
    await loadWords();
    event.target.value = '';
}

function formatTime(date) {
    const h = date.getHours().toString().padStart(2, '0');
    const m = date.getMinutes().toString().padStart(2, '0');
    const s = date.getSeconds().toString().padStart(2, '0');
    return `${h}:${m}:${s}`;
}

function startAutoSave() {
    // Auto-save every 3 minutes (180000 ms)
    if (autoSaveTimer) clearInterval(autoSaveTimer);
    autoSaveTimer = setInterval(async () => {
        await saveWords();
    }, 3 * 60 * 1000);
}

// --- 文件上传与处理 ---

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        selectedFile = e.dataTransfer.files[0];
        fileInput.files = e.dataTransfer.files;
        updateProcessButton();
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        selectedFile = fileInput.files[0];
        updateProcessButton();
    }
});

function countEnabledWords() {
    const tbody = document.getElementById('wordsTable');
    const checkboxes = tbody.querySelectorAll('input[type="checkbox"]');
    let count = 0;
    checkboxes.forEach(cb => { if (cb.checked) count++; });
    return count;
}

function updateProcessButton() {
    const enabledCount = countEnabledWords();
    document.getElementById('processBtn').disabled = !(selectedFile && enabledCount > 0);
}

async function processDocument() {
    if (!selectedFile) return;

    const progress = document.getElementById('progress');
    const auditResult = document.getElementById('auditResult');
    const downloadLinks = document.getElementById('downloadLinks');

    progress.classList.remove('d-none');
    auditResult.classList.add('d-none');
    downloadLinks.classList.add('d-none');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const resp = await fetch('/api/process', {method: 'POST', body: formData});
        const data = await resp.json();

        if (data.error) {
            auditResult.innerHTML = `<div class="alert alert-danger">${escapeHtml(data.error)}</div>`;
            auditResult.classList.remove('d-none');
            return;
        }

        // 显示替换统计
        const totalCount = data.total_replacements || 0;
        const counts = data.replacement_counts || {};
        let statsHtml = '';
        if (totalCount > 0) {
            const items = Object.entries(counts).map(([word, count]) =>
                `<li>「${escapeHtml(word)}」已替换 <strong>${count}</strong> 次</li>`
            ).join('');
            statsHtml = `
                <div class="alert alert-info">
                    📊 共替换 <strong>${totalCount}</strong> 处：
                    <ul class="mb-0">${items}</ul>
                </div>`;
        } else {
            statsHtml = `<div class="alert alert-secondary">ℹ️ 未发现需要替换的敏感词</div>`;
        }

        // 显示审计结果
        const audit = data.audit;
        if (audit.is_clean) {
            statsHtml += `<div class="alert alert-success">✅ 审计通过：未检测到残留敏感词</div>`;
        } else {
            statsHtml += `
                <div class="alert alert-warning">
                    ⚠️ 审计发现 ${audit.total_matches} 处残留匹配：
                    <ul class="mb-0">${audit.missed_words.map(m => `<li><strong>${escapeHtml(m.word)}</strong> — ${escapeHtml(m.context)}</li>`).join('')}</ul>
                </div>`;
        }
        auditResult.innerHTML = statsHtml;
        auditResult.classList.remove('d-none');

        // 显示下载链接
        downloadLinks.innerHTML = `
            <a href="${data.download_url}" class="btn btn-primary me-2">下载处理后文档</a>
            <a href="${data.audit_url}" class="btn btn-outline-secondary">下载审计报告</a>`;
        downloadLinks.classList.remove('d-none');

    } catch (err) {
        auditResult.innerHTML = `<div class="alert alert-danger">处理出错：${escapeHtml(err.message)}</div>`;
        auditResult.classList.remove('d-none');
    } finally {
        progress.classList.add('d-none');
    }
}

// 初始化
loadWords();
startAutoSave();
