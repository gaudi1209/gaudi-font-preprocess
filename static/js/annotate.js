/* 标注出图页面逻辑 */

// 状态管理
const state = {
    imageHash: null,
    characters: [],
    outputDir: null,
    exportedDir: null,
    mode: 'traditional',  // 'traditional' 或 'simplified'
    inputText: ''
};

// DOM 元素
const elements = {
    emptyState: document.getElementById('emptyState'),
    cardGrid: document.getElementById('cardGrid'),
    inputCount: document.getElementById('inputCount'),
    cardCount: document.getElementById('cardCount'),
    simplifiedInput: document.getElementById('simplifiedInput'),
    traditionalInput: document.getElementById('traditionalInput'),
    simplifiedMode: document.getElementById('simplifiedMode'),
    traditionalMode: document.getElementById('traditionalMode'),
    importBtn: document.getElementById('importBtn'),
    exportBtn: document.getElementById('exportBtn'),
    csvBtn: document.getElementById('csvBtn'),
    openDirBtn: document.getElementById('openDirBtn'),
    annotateBtn: document.getElementById('annotateBtn'),
    clearBtn: document.getElementById('clearBtn')
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadCharacters();
    setupEventListeners();
});

function setupEventListeners() {
    // 导入按钮
    elements.importBtn.addEventListener('click', importDirectory);

    // 导出按钮
    elements.exportBtn.addEventListener('click', exportImages);
    elements.csvBtn.addEventListener('click', exportCSV);
    elements.openDirBtn.addEventListener('click', openOutputDirectory);

    // 标注按钮
    elements.annotateBtn.addEventListener('click', startAnnotate);
    elements.clearBtn.addEventListener('click', clearInputs);

    // 繁简切换
    elements.simplifiedMode.addEventListener('click', () => setMode('simplified'));
    elements.traditionalMode.addEventListener('click', () => setMode('traditional'));

    // 繁简输入联动（带去标点和防抖）
    let simpDebounceTimer;
    let tradDebounceTimer;
    let isUpdating = false;  // 防止循环更新

    elements.simplifiedInput.addEventListener('input', (e) => {
        if (isUpdating) return;
        clearTimeout(simpDebounceTimer);
        simpDebounceTimer = setTimeout(async () => {
            // 去除标点符号
            const cleaned = removePunctuation(e.target.value);
            if (cleaned !== e.target.value) {
                e.target.value = cleaned;
            }
            // 转换并更新繁体框
            if (cleaned) {
                const result = await callConvertApi('/api/convert_to_traditional', cleaned);
                if (result) {
                    isUpdating = true;
                    elements.traditionalInput.value = result;
                    elements.inputCount.textContent = Array.from(cleaned).length;
                    setTimeout(() => isUpdating = false, 50);
                }
            } else {
                isUpdating = true;
                elements.traditionalInput.value = '';
                elements.inputCount.textContent = 0;
                setTimeout(() => isUpdating = false, 50);
            }
        }, 300);
    });

    elements.traditionalInput.addEventListener('input', (e) => {
        if (isUpdating) return;
        clearTimeout(tradDebounceTimer);
        tradDebounceTimer = setTimeout(async () => {
            // 去除标点符号
            const cleaned = removePunctuation(e.target.value);
            if (cleaned !== e.target.value) {
                e.target.value = cleaned;
            }
            // 转换并更新简体框
            if (cleaned) {
                const result = await callConvertApi('/api/convert_to_simplified', cleaned);
                if (result) {
                    isUpdating = true;
                    elements.simplifiedInput.value = result;
                    elements.inputCount.textContent = Array.from(cleaned).length;
                    setTimeout(() => isUpdating = false, 50);
                }
            } else {
                isUpdating = true;
                elements.simplifiedInput.value = '';
                elements.inputCount.textContent = 0;
                setTimeout(() => isUpdating = false, 50);
            }
        }, 300);
    });
}

// 调用转换API
async function callConvertApi(url, text) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        if (data.success) {
            console.log(`转换: ${text} -> ${data.result}`);
            return data.result;
        } else {
            console.error('转换失败:', data.error);
            return null;
        }
    } catch (error) {
        console.error('转换API调用失败:', error);
        return null;
    }
}

// 去除标点符号（保留中文、英文、数字，支持CJK扩展区）
function removePunctuation(text) {
    // CJK基本区 \u4e00-\u9fff，扩展A \u3400-\u4dbf
    // 扩展B-F需要用u标志匹配补充平面（代理对范围）
    return text.replace(/[^\u3400-\u9fffa-zA-Z0-9\u{20000}-\u{2FA1F}]/gu, '');
}

// 设置模式
function setMode(mode) {
    state.mode = mode;

    if (mode === 'simplified') {
        elements.simplifiedMode.classList.add('active');
        elements.traditionalMode.classList.remove('active');
    } else {
        elements.simplifiedMode.classList.remove('active');
        elements.traditionalMode.classList.add('active');
    }

    // 更新卡片显示
    updateCardsDisplay();
}

// 更新卡片显示（根据繁简模式）
function updateCardsDisplay() {
    const cards = document.querySelectorAll('.char-card');
    cards.forEach(card => {
        const simplifiedRow = card.querySelector('.simplified-row');
        const traditionalRow = card.querySelector('.traditional-row');

        if (state.mode === 'simplified') {
            simplifiedRow.classList.remove('dimmed');
            simplifiedRow.classList.add('highlighted');
            traditionalRow.classList.add('dimmed');
            traditionalRow.classList.remove('highlighted');
        } else {
            traditionalRow.classList.remove('dimmed');
            traditionalRow.classList.add('highlighted');
            simplifiedRow.classList.add('dimmed');
            simplifiedRow.classList.remove('highlighted');
        }
    });
}

// 加载字符数据
async function loadCharacters() {
    state.imageHash = localStorage.getItem('currentImageHash');

    if (!state.imageHash) {
        showEmptyState();
        return;
    }

    try {
        // 尝试加载缩放校正后的数据
        let response = await fetch(`/api/get_scaled_results/${state.imageHash}`);
        let data = await response.json();

        if (!data.success || !data.characters || data.characters.length === 0) {
            // 如果没有缩放校正数据，加载原始切割结果
            response = await fetch(`/api/get_cut_results/${state.imageHash}`);
            data = await response.json();

            if (!data.success) {
                showEmptyState();
                return;
            }
        }

        // 过滤掉已删除和空字符，按传统顺序排序
        const filteredChars = data.characters.filter(c => !c.deleted && !c.is_empty);
        state.characters = getTraditionalOrder(filteredChars);
        state.outputDir = data.output_dir;

        if (state.characters.length === 0) {
            showEmptyState();
            return;
        }

        showCardGrid();
        renderCards();
        updateUI();

    } catch (error) {
        console.error('加载字符数据失败:', error);
        showEmptyState();
    }
}

// 传统书法顺序：从上到下，从右到左
function getTraditionalOrder(characters) {
    return [...characters].sort((a, b) => {
        if (a.strip_index !== b.strip_index) {
            return b.strip_index - a.strip_index;
        }
        return a.char_index - b.char_index;
    });
}

function showEmptyState() {
    elements.emptyState.style.display = 'flex';
    elements.cardGrid.style.display = 'none';
    elements.cardCount.textContent = '0';
}

function showCardGrid() {
    elements.emptyState.style.display = 'none';
    elements.cardGrid.style.display = 'grid';
}

function updateUI() {
    const activeCount = state.characters.filter(c => !c.deleted).length;
    elements.cardCount.textContent = activeCount;
    elements.annotateBtn.disabled = activeCount === 0;
    elements.exportBtn.disabled = activeCount === 0;
    elements.csvBtn.disabled = activeCount === 0;
}

// 渲染卡片
function renderCards() {
    elements.cardGrid.innerHTML = '';

    console.log('渲染卡片, 字符数量:', state.characters.length);

    state.characters.forEach((char, index) => {
        const card = createCharCard(char, index);
        elements.cardGrid.appendChild(card);
    });

    updateCardsDisplay();
    console.log('卡片渲染完成');
}

// 创建字符卡片
function createCharCard(char, index) {
    const card = document.createElement('div');
    card.className = 'char-card';
    card.dataset.index = index;

    // 右键删除
    card.title = '右键点击可删除此字符';
    card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        if (confirm(`删除第 ${index + 1} 个字符？`)) {
            state.characters[index].deleted = true;
            card.classList.add('card-deleted');
            card.style.opacity = '0.3';
            card.style.pointerEvents = 'none';
            updateUI();
        }
    });

    // 获取图片URL
    const imageUrl = char.processed_url || char.image_url || `/output/${state.imageHash}/${char.filename}`;
    const filename = char.filename || char.processed_filename || 'unknown';

    console.log(`创建卡片 ${index}: filename=${filename}, imageUrl=${imageUrl}`);

    card.innerHTML = `
        <div class="card-image">
            <span class="card-filename">${filename}</span>
            <img src="${imageUrl}" alt="字符 ${index + 1}">
        </div>
        <div class="card-info">
            <div class="card-row simplified-row">
                <label>简体:</label>
                <input type="text" class="simplified-input" data-index="${index}">
                <span class="utf-code simplified-utf"></span>
            </div>
            <div class="card-row traditional-row">
                <label>繁体:</label>
                <input type="text" class="traditional-input" data-index="${index}">
                <span class="utf-code traditional-utf"></span>
            </div>
        </div>
    `;

    // 输入事件
    const simpInput = card.querySelector('.simplified-input');
    const tradInput = card.querySelector('.traditional-input');
    const simpUtf = card.querySelector('.simplified-utf');
    const tradUtf = card.querySelector('.traditional-utf');

    simpInput.addEventListener('input', (e) => {
        // 提取第一个完整Unicode码点（支持CJK扩展区代理对）
        const chars = Array.from(e.target.value);
        const char = chars[0] || '';
        if (e.target.value !== char) e.target.value = char;
        simpUtf.textContent = char ? getUtfCode(char) : '';
        state.characters[index].simplified = char;

        // 自动转换繁体
        if (char) {
            convertSingleToTraditional(char, index);
        }
    });

    tradInput.addEventListener('input', (e) => {
        const chars = Array.from(e.target.value);
        const char = chars[0] || '';
        if (e.target.value !== char) e.target.value = char;
        tradUtf.textContent = char ? getUtfCode(char) : '';
        state.characters[index].traditional = char;

        // 自动转换简体
        if (char) {
            convertSingleToSimplified(char, index);
        }
    });

    return card;
}

// 获取UTF编码（支持CJK扩展区等补充平面字符）
function getUtfCode(char) {
    const code = char.codePointAt(0);
    const hexLen = code > 0xFFFF ? 5 : 4;
    return 'U+' + code.toString(16).toUpperCase().padStart(hexLen, '0');
}

// 单字转换
async function convertSingleToTraditional(char, index) {
    try {
        const response = await fetch('/api/convert_to_traditional', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: char })
        });

        const data = await response.json();
        console.log(`单字简转繁: ${char} -> ${data.result}`);
        if (data.success && data.result) {
            const card = document.querySelector(`.char-card[data-index="${index}"]`);
            if (card) {
                const tradInput = card.querySelector('.traditional-input');
                const tradUtf = card.querySelector('.traditional-utf');
                tradInput.value = data.result;
                tradUtf.textContent = getUtfCode(data.result);
                state.characters[index].traditional = data.result;
            }
        }
    } catch (error) {
        console.error('转换失败:', error);
    }
}

async function convertSingleToSimplified(char, index) {
    try {
        const response = await fetch('/api/convert_to_simplified', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: char })
        });

        const data = await response.json();
        console.log(`单字繁转简: ${char} -> ${data.result}`);
        if (data.success && data.result) {
            const card = document.querySelector(`.char-card[data-index="${index}"]`);
            if (card) {
                const simpInput = card.querySelector('.simplified-input');
                const simpUtf = card.querySelector('.simplified-utf');
                simpInput.value = data.result;
                simpUtf.textContent = getUtfCode(data.result);
                state.characters[index].simplified = data.result;
            }
        }
    } catch (error) {
        console.error('转换失败:', error);
    }
}

// 开始标注
function startAnnotate() {
    let text = state.mode === 'simplified'
        ? elements.simplifiedInput.value
        : elements.traditionalInput.value;

    if (!text) {
        showToast('请先输入文字');
        return;
    }

    // 去除标点符号
    text = removePunctuation(text);

    if (!text) {
        showToast('输入的文字不包含有效字符');
        return;
    }

    const chars = Array.from(text);  // 用Array.from正确处理代理对（CJK扩展区）
    const cards = document.querySelectorAll('.char-card');
    let charIdx = 0;

    cards.forEach((card, index) => {
        if (state.characters[index] && state.characters[index].deleted) return;  // 跳过已删除
        if (charIdx < chars.length) {
            const char = chars[charIdx];

            if (state.mode === 'simplified') {
                const simpInput = card.querySelector('.simplified-input');
                const simpUtf = card.querySelector('.simplified-utf');
                simpInput.value = char;
                simpUtf.textContent = getUtfCode(char);
                state.characters[index].simplified = char;
                convertSingleToTraditional(char, index);
            } else {
                const tradInput = card.querySelector('.traditional-input');
                const tradUtf = card.querySelector('.traditional-utf');
                tradInput.value = char;
                tradUtf.textContent = getUtfCode(char);
                state.characters[index].traditional = char;
                convertSingleToSimplified(char, index);
            }
            charIdx++;
        }
    });

    showToast('标注完成');
}

// 清空输入
function clearInputs() {
    elements.simplifiedInput.value = '';
    elements.traditionalInput.value = '';
    elements.inputCount.textContent = 0;

    // 清空所有卡片的标注
    const cards = document.querySelectorAll('.char-card');
    cards.forEach((card, index) => {
        const simpInput = card.querySelector('.simplified-input');
        const tradInput = card.querySelector('.traditional-input');
        const simpUtf = card.querySelector('.simplified-utf');
        const tradUtf = card.querySelector('.traditional-utf');

        simpInput.value = '';
        tradInput.value = '';
        simpUtf.textContent = '';
        tradUtf.textContent = '';

        if (state.characters[index]) {
            state.characters[index].simplified = '';
            state.characters[index].traditional = '';
        }
    });

    showToast('已清空');
}

// 导入目录
async function importDirectory() {
    // 使用Electron的dialog或创建一个文件选择器
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;

    input.onchange = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        showLoading('正在导入...');

        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch('/api/import_characters', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                state.characters = data.characters;
                state.outputDir = data.output_dir;
                state.imageHash = data.hash;

                localStorage.setItem('currentImageHash', state.imageHash);

                showCardGrid();
                renderCards();
                updateUI();

                showToast(`成功导入 ${data.characters.length} 个字符`);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            showToast('导入失败: ' + error.message);
        }

        hideLoading();
    };

    input.click();
}

// 导出白底黑字
async function exportImages() {
    if (state.characters.length === 0) {
        showToast('没有可导出的字符');
        return;
    }

    // 收集标注数据
    const annotations = [];
    state.characters.forEach((char, index) => {
        const card = document.querySelector(`.char-card[data-index="${index}"]`);
        if (card) {
            const primaryChar = state.mode === 'simplified'
                ? card.querySelector('.simplified-input').value
                : card.querySelector('.traditional-input').value;

            if (primaryChar) {
                annotations.push({
                    index: index,
                    filename: char.filename || char.processed_filename,
                    character: primaryChar,
                    simplified: card.querySelector('.simplified-input').value,
                    traditional: card.querySelector('.traditional-input').value
                });
            }
        }
    });

    if (annotations.length === 0) {
        showToast('请先标注字符');
        return;
    }

    showLoading('正在导出...');

    try {
        const response = await fetch('/api/export_annotated', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hash: state.imageHash,
                annotations: annotations,
                mode: state.mode
            })
        });

        const data = await response.json();

        if (data.success) {
            state.exportedDir = data.output_dir;
            elements.openDirBtn.disabled = false;
            showToast(`成功导出 ${data.count} 个字符到 ${data.output_dir}`);

            // 清理中间过程文件
            try {
                const cleanResp = await fetch('/api/cleanup_intermediate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hash: state.imageHash, keep_dir: data.output_dir })
                });
                const cleanData = await cleanResp.json();
                if (cleanData.success) {
                    console.log('中间文件清理完成:', cleanData.message);
                }
            } catch (e) {
                console.warn('清理中间文件失败:', e);
            }
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('导出失败: ' + error.message);
    }

    hideLoading();
}

// 导出CSV
async function exportCSV() {
    if (state.characters.length === 0) {
        showToast('没有可导出的字符');
        return;
    }

    // 收集标注数据
    const annotations = [];
    state.characters.forEach((char, index) => {
        const card = document.querySelector(`.char-card[data-index="${index}"]`);
        if (card) {
            const simpChar = card.querySelector('.simplified-input').value;
            const tradChar = card.querySelector('.traditional-input').value;

            if (simpChar || tradChar) {
                annotations.push({
                    index: index,
                    filename: char.filename || char.processed_filename,
                    simplified: simpChar,
                    traditional: tradChar,
                    primary: state.mode === 'simplified' ? simpChar : tradChar
                });
            }
        }
    });

    if (annotations.length === 0) {
        showToast('请先标注字符');
        return;
    }

    showLoading('正在导出CSV...');

    try {
        const response = await fetch('/api/export_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hash: state.imageHash,
                annotations: annotations,
                mode: state.mode
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`成功导出CSV到 ${data.output_path}`);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('导出失败: ' + error.message);
    }

    hideLoading();
}

// 打开输出目录
async function openOutputDirectory() {
    const dirPath = state.exportedDir || state.outputDir;

    if (!dirPath) {
        showToast('请先导出');
        return;
    }

    try {
        const response = await fetch('/api/open_directory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: dirPath })
        });

        const data = await response.json();

        if (data.success) {
            showToast('已打开目录');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('打开目录失败: ' + error.message);
    }
}
