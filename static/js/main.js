const API = '/api/sensitive-words';
let selectedFile = null;

// --- Sensitive Words Management ---

async function loadWords() {
    const resp = await fetch(API);
    const words = await resp.json();
    const tbody = document.getElementById('wordsTable');
    tbody.innerHTML = '';
    words.forEach(w => {
        tbody.innerHTML += `
            <tr>
                <td><input class="form-control form-control-sm" value="${escapeHtml(w.word)}" onchange="updateWord(${w.id}, this, this.parentElement.previousElementSibling.firstElementChild)"></td>
                <td><input class="form-control form-control-sm" value="${escapeHtml(w.replacement)}" onchange="updateWord(${w.id}, this.previousElementSibling.firstElementChild, this)"></td>
                <td><button class="btn btn-sm btn-danger" onclick="deleteWord(${w.id})">&times;</button></td>
            </tr>`;
    });
    updateProcessButton();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function addWord() {
    const word = document.getElementById('newWord').value.trim();
    const replacement = document.getElementById('newReplacement').value.trim();
    if (!word || !replacement) return alert('Both fields required');

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

async function exportWords() {
    const resp = await fetch(`${API}/export`);
    const data = await resp.json();
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sensitive_words.json';
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
    await fetch(`${API}/import`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    });
    await loadWords();
    event.target.value = '';
}

// --- File Upload & Processing ---

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

function updateProcessButton() {
    const words = document.getElementById('wordsTable').children.length;
    document.getElementById('processBtn').disabled = !(selectedFile && words > 0);
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

        // Show audit
        const audit = data.audit;
        if (audit.is_clean) {
            auditResult.innerHTML = `<div class="alert alert-success">✅ Audit passed: no sensitive words remaining.</div>`;
        } else {
            auditResult.innerHTML = `
                <div class="alert alert-warning">
                    ⚠️ Audit found ${audit.total_matches} remaining match(es):
                    <ul>${audit.missed_words.map(m => `<li><strong>${escapeHtml(m.word)}</strong> — ${escapeHtml(m.context)}</li>`).join('')}</ul>
                </div>`;
        }
        auditResult.classList.remove('d-none');

        // Show download links
        downloadLinks.innerHTML = `
            <a href="${data.download_url}" class="btn btn-primary me-2">Download Processed Document</a>
            <a href="${data.audit_url}" class="btn btn-outline-secondary">Download Audit Report</a>`;
        downloadLinks.classList.remove('d-none');

    } catch (err) {
        auditResult.innerHTML = `<div class="alert alert-danger">Error: ${escapeHtml(err.message)}</div>`;
        auditResult.classList.remove('d-none');
    } finally {
        progress.classList.add('d-none');
    }
}

// Init
loadWords();
