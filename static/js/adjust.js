/* 切割调整页面逻辑 */

// 状态管理
const state = {
    imageHash: null,
    characters: [],
    selectedIndices: [],
    currentAdjustIndex: null
};

// DOM 元素
const elements = {
    loadingState: document.getElementById('loadingState'),
    emptyState: document.getElementById('emptyState'),
    charGrid: document.getElementById('charGrid'),
    totalCount: document.getElementById('totalCount'),
    adjustCount: document.getElementById('adjustCount'),
    adjustInfo: document.getElementById('adjustInfo'),
    saveBtn: document.getElementById('saveBtn'),
    adjustBtn: document.getElementById('adjustBtn')
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadCutResults();
    setupEventListeners();
});

function setupEventListeners() {
    elements.saveBtn.addEventListener('click', saveAdjustments);
    elements.adjustBtn.addEventListener('click', openAdjustModal);
}

// 加载切割结果
async function loadCutResults() {
    // 从 localStorage 获取当前图片哈希
    state.imageHash = localStorage.getItem('currentImageHash');

    if (!state.imageHash) {
        showEmptyState();
        return;
    }

    showLoadingState();

    try {
        const response = await fetch(`/api/get_cut_results/${state.imageHash}`);
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || '加载切割结果失败');
        }

        if (!data.characters || data.characters.length === 0) {
            showEmptyState();
            return;
        }

        state.characters = data.characters;
        renderCharacterGrid();
        updateUI();

    } catch (error) {
        console.error('加载切割结果失败:', error);
        showToast('加载切割结果失败: ' + error.message);
        showEmptyState();
    }
}

function showLoadingState() {
    elements.loadingState.style.display = 'flex';
    elements.emptyState.style.display = 'none';
    elements.charGrid.style.display = 'none';
}

function showEmptyState() {
    elements.loadingState.style.display = 'none';
    elements.emptyState.style.display = 'flex';
    elements.charGrid.style.display = 'none';
    elements.totalCount.textContent = '0';
}

function showGridState() {
    elements.loadingState.style.display = 'none';
    elements.emptyState.style.display = 'none';
    elements.charGrid.style.display = 'grid';
}

// 渲染字符网格
function renderCharacterGrid() {
    showGridState();
    elements.charGrid.innerHTML = '';

    // 按传统顺序渲染图片，编号就是索引+1
    const traditionalOrder = getTraditionalOrder(state.characters);
    traditionalOrder.forEach((char, index) => {
        const card = createCharCard(char, index);
        elements.charGrid.appendChild(card);
    });
}

// 传统书法顺序：从上到下，从右到左
function getTraditionalOrder(characters) {
    // strip_index 大的是右边的列，应该排在前面（先读）
    // 同一列内，char_index 从小到大（从上到下）
    return [...characters].sort((a, b) => {
        if (a.strip_index !== b.strip_index) {
            return b.strip_index - a.strip_index;  // strip_index大的（右边列）排前面
        }
        return a.char_index - b.char_index;  // 同一列，char_index小的（上面）排前面
    });
}

// 创建字符卡片
function createCharCard(char, displayIndex) {
    const card = document.createElement('div');
    card.className = 'char-card' + (char.is_empty ? ' empty' : '');
    card.dataset.index = displayIndex;
    card.dataset.charId = `${char.strip_index}_${char.char_index}`;

    // 编号（从1开始）
    const number = document.createElement('div');
    number.className = 'char-number';
    number.textContent = displayIndex + 1;

    // 图片
    const img = document.createElement('img');
    img.className = 'char-image';
    img.src = char.image_url;
    img.alt = `字符 ${displayIndex + 1}`;

    // 状态标签
    const hasAdjust = (char.adjust_top || 0) > 0 || (char.adjust_bottom || 0) > 0 ||
                      (char.adjust_left || 0) > 0 || (char.adjust_right || 0) > 0;

    if (char.needs_adjust) {
        const status = document.createElement('div');
        status.className = 'char-status needs-adjust';
        status.textContent = '需调整';
        card.appendChild(status);
    } else if (hasAdjust) {
        const status = document.createElement('div');
        status.className = 'char-status adjusted';
        status.textContent = '已调整';
        card.appendChild(status);
    }

    card.appendChild(number);
    card.appendChild(img);

    // 左键点击 - 选择/取消选择
    card.addEventListener('click', () => toggleSelectCard(card, displayIndex));

    // 右键点击 - 删除字符
    card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        deleteCharacter(char, displayIndex);
    });

    return card;
}

// 删除字符
function deleteCharacter(char, displayIndex) {
    if (confirm(`确定要删除第 ${displayIndex + 1} 号字符吗？`)) {
        // 标记为已删除
        char.deleted = true;

        // 从数组中移除
        const index = state.characters.indexOf(char);
        if (index > -1) {
            state.characters.splice(index, 1);
        }

        // 重新渲染
        renderCharacterGrid();
        updateUI();
        showToast(`已删除第 ${displayIndex + 1} 号字符`);
    }
}

// 选择/取消选择卡片
function toggleSelectCard(card, index) {
    card.classList.toggle('selected');

    const idx = state.selectedIndices.indexOf(index);
    if (idx > -1) {
        state.selectedIndices.splice(idx, 1);
    } else {
        state.selectedIndices.push(index);
    }

    updateAdjustButton();
}

// 更新调整按钮状态
function updateAdjustButton() {
    elements.adjustBtn.disabled = state.selectedIndices.length === 0;
}

// 更新UI
function updateUI() {
    const validChars = state.characters.filter(c => !c.is_empty);
    const needsAdjust = state.characters.filter(c => c.needs_adjust);

    elements.totalCount.textContent = validChars.length;

    if (needsAdjust.length > 0) {
        elements.adjustCount.textContent = needsAdjust.length;
        elements.adjustInfo.style.display = 'block';
    } else {
        elements.adjustInfo.style.display = 'none';
    }
}

// Canvas 调整相关状态
const canvasState = {
    char: null,
    img: null,  // 保存加载的图片
    scale: 1,
    isDragging: false,
    dragEdge: null,  // 'top', 'bottom', 'left', 'right'
    startX: 0,
    startY: 0,
    originalTop: 0,
    originalBottom: 0,
    originalLeft: 0,
    originalRight: 0
};

// 打开调整弹窗
function openAdjustModal() {
    if (state.selectedIndices.length === 0) return;

    // 从第一个选中的开始调整
    state.currentAdjustIndex = state.selectedIndices[0];
    showAdjustModal(state.currentAdjustIndex);
}

// 显示调整弹窗
function showAdjustModal(displayIndex) {
    const orderedChars = getTraditionalOrder(state.characters);
    const char = orderedChars[displayIndex];

    if (!char) return;

    // 创建弹窗
    let modal = document.getElementById('adjustModal');
    if (!modal) {
        modal = createAdjustModal();
        document.body.appendChild(modal);
    }

    // 更新弹窗内容
    document.getElementById('modalCharIndex').textContent = displayIndex + 1;
    document.getElementById('adjustTop').value = char.adjust_top || 0;
    document.getElementById('adjustBottom').value = char.adjust_bottom || 0;
    document.getElementById('adjustLeft').value = char.adjust_left || 0;
    document.getElementById('adjustRight').value = char.adjust_right || 0;

    // 加载图片到 canvas
    loadCharToCanvas(char);

    modal.classList.remove('hidden');
}

// 创建调整弹窗
function createAdjustModal() {
    const modal = document.createElement('div');
    modal.id = 'adjustModal';
    modal.className = 'adjust-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>调整字符 - <span id="modalCharIndex">1</span></h3>
                <button class="btn btn-secondary" onclick="closeAdjustModal()">关闭</button>
            </div>
            <div class="modal-body">
                <div class="preview-area">
                    <canvas id="adjustCanvas"></canvas>
                </div>
                <div class="modal-sidebar">
                    <div class="adjust-controls">
                        <h4>切割范围</h4>
                        <div class="control-row">
                            <label>上边距</label>
                            <input type="number" id="adjustTop" value="0" min="0">
                        </div>
                        <div class="control-row">
                            <label>下边距</label>
                            <input type="number" id="adjustBottom" value="0" min="0">
                        </div>
                        <div class="control-row">
                            <label>左边距</label>
                            <input type="number" id="adjustLeft" value="0" min="0">
                        </div>
                        <div class="control-row">
                            <label>右边距</label>
                            <input type="number" id="adjustRight" value="0" min="0">
                        </div>
                    </div>
                    <div class="adjust-controls">
                        <h4>操作</h4>
                        <button class="btn btn-secondary" style="width: 100%; margin-bottom: 8px;" onclick="resetAdjust()">重置</button>
                        <button class="btn btn-primary" style="width: 100%; margin-bottom: 8px;" onclick="applyAdjust()">应用</button>
                        <button class="btn btn-success" style="width: 100%;" onclick="saveAndNext()">保存并下一个</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    return modal;
}

// 加载字符到 Canvas
function loadCharToCanvas(char) {
    const canvas = document.getElementById('adjustCanvas');

    // 保存当前字符到状态
    canvasState.char = char;

    const img = new Image();
    img.onload = () => {
        // 保存图片对象
        canvasState.img = img;

        // 设置 canvas 大小
        const maxSize = 500;
        canvasState.scale = Math.min(maxSize / img.width, maxSize / img.height);
        canvas.width = img.width * canvasState.scale;
        canvas.height = img.height * canvasState.scale;

        // 绘制图片和边框
        redrawCanvas();

        // 设置canvas事件监听
        setupCanvasEvents(canvas);
    };
    img.src = char.image_url;
}

// 重绘Canvas
function redrawCanvas() {
    const canvas = document.getElementById('adjustCanvas');
    const ctx = canvas.getContext('2d');
    const char = canvasState.char;
    const img = canvasState.img;

    if (!char || !img) return;

    // 清空并重绘图片
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    drawAdjustBox(ctx, canvas.width, canvas.height, char, canvasState.scale);
}

// 绘制调整框（始终显示）
function drawAdjustBox(ctx, canvasWidth, canvasHeight, char, scale) {
    const top = (char.adjust_top || 0) * scale;
    const bottom = (char.adjust_bottom || 0) * scale;
    const left = (char.adjust_left || 0) * scale;
    const right = (char.adjust_right || 0) * scale;

    // 绘制裁剪区域外的遮罩
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';

    // 上边遮罩
    if (top > 0) {
        ctx.fillRect(0, 0, canvasWidth, top);
    }
    // 下边遮罩
    if (bottom > 0) {
        ctx.fillRect(0, canvasHeight - bottom, canvasWidth, bottom);
    }
    // 左边遮罩
    if (left > 0) {
        ctx.fillRect(0, top, left, canvasHeight - top - bottom);
    }
    // 右边遮罩
    if (right > 0) {
        ctx.fillRect(canvasWidth - right, top, right, canvasHeight - top - bottom);
    }

    // 计算边框位置
    const x = left;
    const y = top;
    const w = canvasWidth - left - right;
    const h = canvasHeight - top - bottom;

    // 绘制裁剪边框（绿色更明显）
    ctx.strokeStyle = '#2ecc71';
    ctx.lineWidth = 3;
    ctx.setLineDash([]);
    ctx.strokeRect(x, y, w, h);

    // 绘制四条可拖动的边（红色粗线）
    ctx.fillStyle = '#e74c3c';
    const edgeThickness = 6;

    // 上边手柄
    ctx.fillRect(x, Math.max(0, y - edgeThickness/2), w, edgeThickness);
    // 下边手柄
    ctx.fillRect(x, Math.min(canvasHeight - edgeThickness, y + h - edgeThickness/2), w, edgeThickness);
    // 左边手柄
    ctx.fillRect(Math.max(0, x - edgeThickness/2), y, edgeThickness, h);
    // 右边手柄
    ctx.fillRect(Math.min(canvasWidth - edgeThickness, x + w - edgeThickness/2), y, edgeThickness, h);

    // 绘制四个角的手柄（更大的圆角方块）
    const handleSize = 14;
    ctx.fillStyle = '#e74c3c';

    // 左上角
    drawCornerHandle(ctx, x, y, handleSize, 'top-left');
    // 右上角
    drawCornerHandle(ctx, x + w, y, handleSize, 'top-right');
    // 左下角
    drawCornerHandle(ctx, x, y + h, handleSize, 'bottom-left');
    // 右下角
    drawCornerHandle(ctx, x + w, y + h, handleSize, 'bottom-right');
}

// 绘制角落手柄
function drawCornerHandle(ctx, cx, cy, size, position) {
    ctx.beginPath();
    ctx.arc(cx, cy, size/2, 0, Math.PI * 2);
    ctx.fill();
}

// 设置Canvas事件
function setupCanvasEvents(canvas) {
    // 移除旧的事件监听器
    canvas.onmousedown = null;
    canvas.onmousemove = null;
    canvas.onmouseup = null;
    canvas.onmouseleave = null;

    canvas.onmousedown = handleMouseDown;
    canvas.onmousemove = handleMouseMove;
    canvas.onmouseup = handleMouseUp;
    canvas.onmouseleave = handleMouseUp;
}

// 将鼠标坐标转换为canvas内部坐标
function getCanvasCoords(e) {
    const canvas = e.target;
    const rect = canvas.getBoundingClientRect();

    // 计算缩放比例（CSS尺寸 vs Canvas内部尺寸）
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    // 转换坐标
    const x = (e.clientX - rect.left) * scaleX;
    const y = (e.clientY - rect.top) * scaleY;

    return { x, y, rect };
}

// 检测鼠标在哪个边上
function getEdgeAtPosition(x, y) {
    const char = canvasState.char;
    const scale = canvasState.scale;
    const threshold = 30; // 增大检测阈值

    const top = (char.adjust_top || 0) * scale;
    const bottom = (char.adjust_bottom || 0) * scale;
    const left = (char.adjust_left || 0) * scale;
    const right = (char.adjust_right || 0) * scale;

    const canvas = document.getElementById('adjustCanvas');
    const boxLeft = left;
    const boxTop = top;
    const boxRight = canvas.width - right;
    const boxBottom = canvas.height - bottom;

    // 检测右边 - x 在右边界附近
    if (x >= boxRight - threshold && x <= canvas.width &&
        y >= boxTop && y <= boxBottom) {
        return 'right';
    }
    // 检测下边 - y 在下边界附近
    if (y >= boxBottom - threshold && y <= canvas.height &&
        x >= boxLeft && x <= boxRight) {
        return 'bottom';
    }
    // 检测上边
    if (y >= Math.max(0, boxTop - threshold) && y <= boxTop + threshold &&
        x >= boxLeft && x <= boxRight) {
        return 'top';
    }
    // 检测左边
    if (x >= Math.max(0, boxLeft - threshold) && x <= boxLeft + threshold &&
        y >= boxTop && y <= boxBottom) {
        return 'left';
    }

    return null;
}

// 鼠标按下
function handleMouseDown(e) {
    const { x, y } = getCanvasCoords(e);

    const edge = getEdgeAtPosition(x, y);
    if (edge) {
        canvasState.isDragging = true;
        canvasState.dragEdge = edge;
        canvasState.startX = x;
        canvasState.startY = y;
        canvasState.originalTop = canvasState.char.adjust_top || 0;
        canvasState.originalBottom = canvasState.char.adjust_bottom || 0;
        canvasState.originalLeft = canvasState.char.adjust_left || 0;
        canvasState.originalRight = canvasState.char.adjust_right || 0;
    }
}

// 鼠标移动
function handleMouseMove(e) {
    const { x, y, rect } = getCanvasCoords(e);
    const canvas = e.target;

    if (canvasState.isDragging) {
        const dx = x - canvasState.startX;
        const dy = y - canvasState.startY;
        const scale = canvasState.scale;

        // 根据拖动的边更新调整值
        switch (canvasState.dragEdge) {
            case 'top':
                canvasState.char.adjust_top = Math.max(0, canvasState.originalTop + dy / scale);
                document.getElementById('adjustTop').value = Math.round(canvasState.char.adjust_top);
                break;
            case 'bottom':
                canvasState.char.adjust_bottom = Math.max(0, canvasState.originalBottom - dy / scale);
                document.getElementById('adjustBottom').value = Math.round(canvasState.char.adjust_bottom);
                break;
            case 'left':
                canvasState.char.adjust_left = Math.max(0, canvasState.originalLeft + dx / scale);
                document.getElementById('adjustLeft').value = Math.round(canvasState.char.adjust_left);
                break;
            case 'right':
                canvasState.char.adjust_right = Math.max(0, canvasState.originalRight - dx / scale);
                document.getElementById('adjustRight').value = Math.round(canvasState.char.adjust_right);
                break;
        }

        // 重绘canvas
        redrawCanvas();
    } else {
        // 更新光标样式
        const edge = getEdgeAtPosition(x, y);
        if (edge === 'top' || edge === 'bottom') {
            canvas.style.cursor = 'ns-resize';
        } else if (edge === 'left' || edge === 'right') {
            canvas.style.cursor = 'ew-resize';
        } else {
            canvas.style.cursor = 'crosshair';
        }
    }
}

// 鼠标释放
function handleMouseUp(e) {
    canvasState.isDragging = false;
    canvasState.dragEdge = null;
}

// 关闭调整弹窗
function closeAdjustModal() {
    const modal = document.getElementById('adjustModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    // 清除选择状态
    state.selectedIndices = [];
    state.currentAdjustIndex = null;
    // 刷新字符网格显示
    renderCharacterGrid();
    updateAdjustButton();
}

// 重置调整
function resetAdjust() {
    if (canvasState.char) {
        canvasState.char.adjust_top = 0;
        canvasState.char.adjust_bottom = 0;
        canvasState.char.adjust_left = 0;
        canvasState.char.adjust_right = 0;
    }
    document.getElementById('adjustTop').value = 0;
    document.getElementById('adjustBottom').value = 0;
    document.getElementById('adjustLeft').value = 0;
    document.getElementById('adjustRight').value = 0;
    redrawCanvas();
}

// 应用调整
function applyAdjust() {
    // canvasState.char 和 orderedChars[state.currentAdjustIndex] 应该是同一个引用
    // 拖动时已经直接修改了 canvasState.char，所以这里只需要同步输入框的值
    if (canvasState.char) {
        // 从输入框获取最终值（用户可能手动输入）
        canvasState.char.adjust_top = parseInt(document.getElementById('adjustTop').value) || 0;
        canvasState.char.adjust_bottom = parseInt(document.getElementById('adjustBottom').value) || 0;
        canvasState.char.adjust_left = parseInt(document.getElementById('adjustLeft').value) || 0;
        canvasState.char.adjust_right = parseInt(document.getElementById('adjustRight').value) || 0;
        canvasState.char.needs_adjust = false;
    }

    // 重新加载 canvas
    redrawCanvas();
    showToast('调整已应用');
}

// 保存并下一个
async function saveAndNext() {
    applyAdjust();

    // 找到下一个需要调整的
    const currentIndex = state.selectedIndices.indexOf(state.currentAdjustIndex);
    if (currentIndex < state.selectedIndices.length - 1) {
        state.currentAdjustIndex = state.selectedIndices[currentIndex + 1];
        showAdjustModal(state.currentAdjustIndex);
    } else {
        closeAdjustModal();
        showToast('所有选中字符已调整完成');
    }
}

// 保存调整结果
async function saveAdjustments() {
    if (!state.imageHash) {
        showToast('没有可保存的数据');
        return;
    }

    showLoading('保存中...');

    try {
        const response = await fetch('/api/save_adjustments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hash: state.imageHash,
                characters: state.characters
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast('保存成功');
            // 更新显示
            renderCharacterGrid();
            updateUI();
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('保存失败: ' + error.message);
    }

    hideLoading();
}
