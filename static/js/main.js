const API = '/api/sensitive-words';
let selectedFile = null;
let autoSaveTimer = null;
let isBatchMode = false;
let batchFiles = [];

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
    if (autoSaveTimer) clearInterval(autoSaveTimer);
    autoSaveTimer = setInterval(async () => {
        await saveWords();
    }, 3 * 60 * 1000);
}

// --- 批量模式切换 ---

function toggleBatchMode() {
    isBatchMode = !isBatchMode;
    const batchBtn = document.getElementById('batchProcessBtn');
    const batchFileInput = document.getElementById('batchFileInput');
    const fileList = document.getElementById('fileList');
    const batchSubmitBtn = document.getElementById('batchSubmitBtn');
    const fileInput = document.getElementById('fileInput');

    if (isBatchMode) {
        batchBtn.textContent = '单文件处理';
        batchFileInput.classList.remove('d-none');
        fileInput.classList.add('d-none');
        fileList.classList.remove('d-none');
        batchSubmitBtn.classList.remove('d-none');
        document.getElementById('processBtn').classList.add('d-none');
    } else {
        batchBtn.textContent = '批量处理';
        batchFileInput.classList.add('d-none');
        fileInput.classList.remove('d-none');
        fileList.classList.add('d-none');
        batchSubmitBtn.classList.add('d-none');
        document.getElementById('processBtn').classList.remove('d-none');
        batchFiles = [];
        updateBatchFileList();
    }
}

// --- 文件管理 ---

document.getElementById('batchFileInput').addEventListener('change', (e) => {
    const files = Array.from(e.target.files);
    files.forEach(f => {
        const ext = f.name.split('.').pop().toLowerCase();
        if (['docx', 'txt', 'pdf'].includes(ext)) {
            batchFiles.push(f);
        }
    });
    updateBatchFileList();
    document.getElementById('batchSubmitBtn').disabled = batchFiles.length === 0;
    e.target.value = '';
});

function updateBatchFileList() {
    const container = document.getElementById('batchFilesList');
    const countEl = document.getElementById('fileCount');
    countEl.textContent = `已选择 ${batchFiles.length} 个文件`;
    container.innerHTML = '';
    batchFiles.forEach((f, idx) => {
        const div = document.createElement('div');
        div.className = 'd-flex justify-content-between align-items-center py-1';
        div.innerHTML = `
            <small class="text-truncate me-2">${escapeHtml(f.name)} <span class="text-muted">(${formatFileSize(f.size)})</span></small>
            <button class="btn btn-sm btn-outline-danger py-0 px-1" onclick="removeBatchFile(${idx})">×</button>
        `;
        container.appendChild(div);
    });
}

function removeBatchFile(idx) {
    batchFiles.splice(idx, 1);
    updateBatchFileList();
    document.getElementById('batchSubmitBtn').disabled = batchFiles.length === 0;
}

function clearBatchFiles() {
    batchFiles = [];
    updateBatchFileList();
    document.getElementById('batchSubmitBtn').disabled = true;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

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

// --- 单文件处理 ---

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
        if (isBatchMode) {
            // In batch mode, add all dropped files
            Array.from(e.dataTransfer.files).forEach(f => {
                const ext = f.name.split('.').pop().toLowerCase();
                if (['docx', 'txt', 'pdf'].includes(ext)) batchFiles.push(f);
            });
            updateBatchFileList();
            document.getElementById('batchSubmitBtn').disabled = batchFiles.length === 0;
        } else {
            selectedFile = e.dataTransfer.files[0];
            fileInput.files = e.dataTransfer.files;
            updateProcessButton();
        }
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        selectedFile = fileInput.files[0];
        updateProcessButton();
    }
});

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
    formData.append('track_changes', document.getElementById('trackChangesMode').checked ? 'true' : 'false');

    try {
        const resp = await fetch('/api/process', {method: 'POST', body: formData});
        const data = await resp.json();

        if (data.error) {
            auditResult.innerHTML = `<div class="alert alert-danger">${escapeHtml(data.error)}</div>`;
            auditResult.classList.remove('d-none');
            return;
        }

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

// --- 批量处理 ---

async function processBatch() {
    if (batchFiles.length === 0) return;

    const enabledCount = countEnabledWords();
    if (enabledCount === 0) return alert('请先添加并启用敏感词');

    const batchProgress = document.getElementById('batchProgress');
    const batchProgressBar = document.getElementById('batchProgressBar');
    const batchProgressText = document.getElementById('batchProgressText');
    const batchResult = document.getElementById('batchResult');
    const downloadLinks = document.getElementById('downloadLinks');

    batchProgress.classList.remove('d-none');
    batchResult.classList.add('d-none');
    downloadLinks.classList.add('d-none');

    const trackChanges = document.getElementById('trackChangesMode').checked;
    let successCount = 0;
    let failCount = 0;
    let totalReplacements = 0;
    const results = [];

    for (let i = 0; i < batchFiles.length; i++) {
        const file = batchFiles[i];
        batchProgressText.textContent = `正在处理 ${i + 1}/${batchFiles.length}：${file.name}`;
        batchProgressBar.style.width = `${((i + 1) / batchFiles.length) * 100}%`;

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('track_changes', trackChanges ? 'true' : 'false');

            const resp = await fetch('/api/process', {method: 'POST', body: formData});
            const data = await resp.json();

            if (data.error) {
                failCount++;
                results.push({name: file.name, status: 'error', error: data.error});
            } else {
                successCount++;
                totalReplacements += data.total_replacements || 0;
                results.push({name: file.name, status: 'success', replacements: data.total_replacements, download_url: data.download_url, audit_url: data.audit_url});
            }
        } catch (err) {
            failCount++;
            results.push({name: file.name, status: 'error', error: err.message});
        }
    }

    // Show results
    let resultHtml = `
        <div class="alert ${failCount === 0 ? 'alert-success' : 'alert-warning'}">
            📊 批量处理完成：成功 <strong>${successCount}</strong> 个，失败 <strong>${failCount}</strong> 个，共替换 <strong>${totalReplacements}</strong> 处
        </div>`;

    // Show individual results
    resultHtml += '<div class="list-group">';
    results.forEach(r => {
        if (r.status === 'success') {
            resultHtml += `
                <div class="list-group-item list-group-item-success d-flex justify-content-between align-items-center">
                    <span>✅ ${escapeHtml(r.name)}（替换 ${r.replacements} 处）</span>
                    <div>
                        <a href="${r.download_url}" class="btn btn-sm btn-primary me-1">下载</a>
                        <a href="${r.audit_url}" class="btn btn-sm btn-outline-secondary">审计</a>
                    </div>
                </div>`;
        } else {
            resultHtml += `
                <div class="list-group-item list-group-item-danger">
                    ❌ ${escapeHtml(r.name)}：${escapeHtml(r.error)}
                </div>`;
        }
    });
    resultHtml += '</div>';

    batchResult.innerHTML = resultHtml;
    batchResult.classList.remove('d-none');
    batchProgress.classList.add('d-none');
}

// 初始化
loadWords();
startAutoSave();
