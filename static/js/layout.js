/* 切割布局页面逻辑 - 支持缩放和文本框显示 */

// 状态管理
const state = {
    imageHash: null,
    imageUrl: null,
    imageWidth: 0,
    imageHeight: 0,
    canvasWidth: 0,
    canvasHeight: 0,
    originalScale: 1,  // 原始适配比例
    zoomLevel: 1,      // 缩放级别
    panOffset: { x: 0, y: 0 },  // 平移偏移
    verticalLines: [],
    horizontalLines: [],
    boxes: [],         // OCR文本框
    imageObj: null,
    selectedLine: null,
    lineType: null,
    isDragging: false,
    isPanning: false,
    lastMousePos: null,
    showTextBoxes: true  // 是否显示文本框
};

// DOM 元素
const canvas = document.getElementById('imageCanvas');
const ctx = canvas.getContext('2d');
const imageInput = document.getElementById('imageInput');
const uploadBtn = document.getElementById('uploadBtn');
const saveBtn = document.getElementById('saveBtn');
const applyBtn = document.getElementById('applyBtn');
const emptyState = document.getElementById('emptyState');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    resizeCanvas();
});

function setupEventListeners() {
    uploadBtn.addEventListener('click', () => imageInput.click());
    imageInput.addEventListener('change', handleImageUpload);
    saveBtn.addEventListener('click', saveCutLines);
    applyBtn.addEventListener('click', applyCut);

    // Canvas 事件
    canvas.addEventListener('mousedown', handleMouseDown);
    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('mouseup', handleMouseUp);
    canvas.addEventListener('mouseleave', handleMouseUp);
    canvas.addEventListener('dblclick', handleDoubleClick);
    canvas.addEventListener('wheel', handleWheel, { passive: false });
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());  // 禁止右键菜单

    // 窗口大小变化
    window.addEventListener('resize', resizeCanvas);
}

function resizeCanvas() {
    const workspace = document.querySelector('.workspace');
    canvas.width = workspace.clientWidth;
    canvas.height = workspace.clientHeight;
    state.canvasWidth = canvas.width;
    state.canvasHeight = canvas.height;

    // 计算原始适配比例
    if (state.imageObj) {
        calculateBaseScale();
        drawCanvas();
    }
}

function calculateBaseScale() {
    // 计算图片完全适配canvas的基础缩放比例
    const imgRatio = state.imageWidth / state.imageHeight;
    const canvasRatio = canvas.width / canvas.height;

    if (imgRatio > canvasRatio) {
        state.originalScale = canvas.width / state.imageWidth;
    } else {
        state.originalScale = canvas.height / state.imageHeight;
    }
}

async function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    showLoading('正在处理图片...');

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error);
        }

        // 更新状态
        state.imageHash = data.hash;
        state.imageWidth = data.width;
        state.imageHeight = data.height;
        state.verticalLines = data.vertical_lines || [];
        state.horizontalLines = data.horizontal_lines || [];
        state.stripHorizontalLines = data.strip_horizontal_lines || [];  // 按列分组的横向切割线
        state.boxes = data.boxes || [];
        state.zoomLevel = 1;
        state.panOffset = { x: 0, y: 0 };

        // 保存到 localStorage 供其他页面使用
        localStorage.setItem('currentImageHash', data.hash);

        // 加载图片
        const img = new Image();
        img.onload = () => {
            state.imageObj = img;
            emptyState.classList.add('hidden');
            calculateBaseScale();
            drawCanvas();
            updateUI();
            hideLoading();

            if (data.has_saved_session) {
                showToast('已加载保存的切割线配置');
            }
        };
        img.src = data.image_url;
        state.imageUrl = data.image_url;

        // 更新信息显示
        document.getElementById('imgWidth').textContent = data.width;
        document.getElementById('imgHeight').textContent = data.height;
        document.getElementById('imgHash').textContent = data.hash.substring(0, 12) + '...';

        // 启用按钮
        saveBtn.disabled = false;
        applyBtn.disabled = false;

    } catch (error) {
        hideLoading();
        showToast('上传失败: ' + error.message);
        console.error(error);
    }
}

// 获取当前绘制参数
function getDrawParams() {
    const scale = state.originalScale * state.zoomLevel;
    const drawWidth = state.imageWidth * scale;
    const drawHeight = state.imageHeight * scale;

    // 居中位置 + 平移偏移
    const baseX = (canvas.width - drawWidth) / 2 + state.panOffset.x;
    const baseY = (canvas.height - drawHeight) / 2 + state.panOffset.y;

    return { scale, drawWidth, drawHeight, offsetX: baseX, offsetY: baseY };
}

function drawCanvas() {
    if (!state.imageObj) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const { scale, drawWidth, drawHeight, offsetX, offsetY } = getDrawParams();

    // 保存绘制参数
    state.drawOffset = { x: offsetX, y: offsetY };
    state.drawScale = scale;

    // 绘制图片
    ctx.drawImage(state.imageObj, offsetX, offsetY, drawWidth, drawHeight);

    // 绘制文本框
    if (state.showTextBoxes && state.boxes.length > 0) {
        drawTextBoxes();
    }

    // 绘制切割线
    drawCutLines();
}

function drawTextBoxes() {
    const { x: offsetX, y: offsetY } = state.drawOffset;
    const scale = state.drawScale;

    ctx.strokeStyle = 'rgba(46, 204, 113, 0.6)';  // 绿色文本框
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    state.boxes.forEach((box, index) => {
        const x = offsetX + box.x_min * scale;
        const y = offsetY + box.y_min * scale;
        const w = box.width * scale;
        const h = box.height * scale;

        ctx.strokeRect(x, y, w, h);

        // 绘制编号（小字）
        ctx.setLineDash([]);
        ctx.fillStyle = 'rgba(46, 204, 113, 0.9)';
        const fontSize = Math.max(8, 12 / state.zoomLevel);
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(`${index + 1}`, x + 2, y + 2);
        ctx.setLineDash([4, 4]);
    });

    ctx.setLineDash([]);
}

function drawCutLines() {
    const { x: offsetX, y: offsetY } = state.drawOffset;
    const scale = state.drawScale;

    // 绘制纵向切割线（红色）
    ctx.strokeStyle = '#e74c3c';
    ctx.lineWidth = 2 / state.zoomLevel;  // 线宽随缩放调整
    state.verticalLines.forEach(x => {
        const canvasX = offsetX + x * scale;
        ctx.beginPath();
        ctx.moveTo(canvasX, offsetY);
        ctx.lineTo(canvasX, offsetY + state.imageHeight * scale);
        ctx.stroke();
    });

    // 绘制横向切割线（蓝色）- 按列绘制，不跨列
    ctx.strokeStyle = '#3498db';
    if (state.stripHorizontalLines && state.stripHorizontalLines.length > 0) {
        // 按列绘制横向切割线
        state.stripHorizontalLines.forEach(strip => {
            const xStart = offsetX + strip.x_start * scale;
            const xEnd = offsetX + strip.x_end * scale;
            strip.horizontal_lines.forEach(y => {
                const canvasY = offsetY + y * scale;
                ctx.beginPath();
                ctx.moveTo(xStart, canvasY);
                ctx.lineTo(xEnd, canvasY);
                ctx.stroke();
            });
        });
    } else {
        // 兼容旧数据：如果没有按列分组的数据，则跨整行绘制
        state.horizontalLines.forEach(y => {
            const canvasY = offsetY + y * scale;
            ctx.beginPath();
            ctx.moveTo(offsetX, canvasY);
            ctx.lineTo(offsetX + state.imageWidth * scale, canvasY);
            ctx.stroke();
        });
    }
}

// 滚轮缩放
function handleWheel(e) {
    e.preventDefault();
    if (!state.imageObj) return;

    const pos = getCanvasPosition(e);
    const oldPos = canvasToImage(pos);

    // 缩放因子
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    const newZoomLevel = Math.max(0.1, Math.min(10, state.zoomLevel * zoomFactor));

    state.zoomLevel = newZoomLevel;

    // 重新计算位置，保持鼠标下的点不动
    const { scale, offsetX, offsetY } = getDrawParams();
    state.drawOffset = { x: offsetX, y: offsetY };
    state.drawScale = scale;

    const newPos = imageToCanvas(oldPos);
    state.panOffset.x += pos.x - newPos.x;
    state.panOffset.y += pos.y - newPos.y;

    drawCanvas();
    updateUI();
}

function imageToCanvas(imagePos) {
    const { x: offsetX, y: offsetY } = state.drawOffset || getDrawParams();
    const scale = state.drawScale || state.originalScale * state.zoomLevel;
    return {
        x: offsetX + imagePos.x * scale,
        y: offsetY + imagePos.y * scale
    };
}

function handleMouseDown(e) {
    if (!state.imageObj) return;

    const pos = getCanvasPosition(e);

    // 右键：平移
    if (e.button === 2) {
        state.isPanning = true;
        state.lastMousePos = pos;
        canvas.style.cursor = 'grabbing';
        e.preventDefault();
        return;
    }

    // 左键处理
    if (e.button !== 0) return;

    const lineInfo = findNearestLine(pos);

    if (lineInfo && e.altKey) {
        // Alt+点击删除切割线
        deleteLine(lineInfo);
    } else if (lineInfo) {
        // 开始拖动切割线
        state.selectedLine = lineInfo.lineIndex !== undefined ? lineInfo.lineIndex : lineInfo.index;
        state.lineType = lineInfo.type;
        state.selectedLineValue = lineInfo.yValue;
        state.selectedStripIndex = lineInfo.stripIndex;  // 存储列索引
        state.isDragging = true;
        canvas.style.cursor = lineInfo.type === 'vertical' ? 'ew-resize' : 'ns-resize';
    }
}

function handleMouseMove(e) {
    if (!state.imageObj) return;

    const pos = getCanvasPosition(e);

    if (state.isPanning && state.lastMousePos) {
        // 平移
        const dx = pos.x - state.lastMousePos.x;
        const dy = pos.y - state.lastMousePos.y;
        state.panOffset.x += dx;
        state.panOffset.y += dy;
        state.lastMousePos = pos;
        drawCanvas();
    } else if (state.isDragging && state.selectedLine !== null) {
        // 拖动切割线
        const imagePos = canvasToImage(pos);

        if (state.lineType === 'vertical') {
            const newX = Math.max(0, Math.min(state.imageWidth, imagePos.x));
            const roundedX = Math.round(newX);
            state.verticalLines[state.selectedLine] = roundedX;

            // 同步更新 stripHorizontalLines 中对应列的边界
            const lineIdx = state.selectedLine;
            if (state.stripHorizontalLines && state.stripHorizontalLines.length > 0) {
                // 移动 verticalLines[lineIdx] 影响 strip[lineIdx-1].x_end 和 strip[lineIdx].x_start
                if (lineIdx > 0 && lineIdx - 1 < state.stripHorizontalLines.length) {
                    state.stripHorizontalLines[lineIdx - 1].x_end = roundedX;
                }
                if (lineIdx < state.stripHorizontalLines.length) {
                    state.stripHorizontalLines[lineIdx].x_start = roundedX;
                }
            }
        } else {
            // 横向切割线 - 只更新当前列
            const newY = Math.max(0, Math.min(state.imageHeight, imagePos.y));
            const roundedY = Math.round(newY);

            // 只更新当前列的横向切割线
            if (state.stripHorizontalLines && state.selectedStripIndex !== undefined) {
                const strip = state.stripHorizontalLines[state.selectedStripIndex];
                if (strip && state.selectedLine < strip.horizontal_lines.length) {
                    strip.horizontal_lines[state.selectedLine] = roundedY;
                    strip.horizontal_lines.sort((a, b) => a - b);
                    state.selectedLine = strip.horizontal_lines.indexOf(roundedY);
                    state.selectedLineValue = roundedY;
                }
            }
        }

        drawCanvas();
        updateUI();
    } else {
        // 检查是否靠近切割线，更新光标
        const lineInfo = findNearestLine(pos);
        if (lineInfo) {
            canvas.style.cursor = lineInfo.type === 'vertical' ? 'ew-resize' : 'ns-resize';
        } else {
            canvas.style.cursor = 'crosshair';
        }
    }
}

function handleMouseUp(e) {
    state.isDragging = false;
    state.isPanning = false;
    state.selectedLine = null;
    state.lineType = null;
    state.lastMousePos = null;
    canvas.style.cursor = 'crosshair';
}

function handleDoubleClick(e) {
    if (!state.imageObj) return;

    const pos = getCanvasPosition(e);
    const imagePos = canvasToImage(pos);

    // Shift+双击：添加竖向切割线
    if (e.shiftKey) {
        addLineAt('vertical', imagePos.x);
        return;
    }

    // 找到鼠标所在的列索引
    let stripIndex = 0;
    if (state.stripHorizontalLines && state.stripHorizontalLines.length > 0) {
        for (let i = 0; i < state.stripHorizontalLines.length; i++) {
            const strip = state.stripHorizontalLines[i];
            if (strip.x_start <= imagePos.x && imagePos.x <= strip.x_end) {
                stripIndex = i;
                break;
            }
        }
    }

    // 普通双击：添加横向切割线到当前列
    addHorizontalLineAt(imagePos.y, stripIndex);
}

// 在指定列添加横向切割线
function addHorizontalLineAt(y, stripIndex) {
    const roundedY = Math.round(y);

    console.log(`添加横向切割线: y=${roundedY}, stripIndex=${stripIndex}`);
    console.log(`当前列信息:`, state.stripHorizontalLines.map((s, i) =>
        `列${i}: x=${s.x_start}-${s.x_end}, 横线数=${s.horizontal_lines.length}`
    ).join(', '));

    if (state.stripHorizontalLines && state.stripHorizontalLines[stripIndex]) {
        const strip = state.stripHorizontalLines[stripIndex];
        // 检查是否已存在
        if (!strip.horizontal_lines.includes(roundedY)) {
            strip.horizontal_lines.push(roundedY);
            strip.horizontal_lines.sort((a, b) => a - b);
            console.log(`已添加到列${stripIndex}, 现有横线:`, strip.horizontal_lines);
        }
    }

    drawCanvas();
    updateUI();
    showToast(`已添加横向切割线`);
}

function getCanvasPosition(e) {
    const rect = canvas.getBoundingClientRect();
    return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top
    };
}

function canvasToImage(canvasPos) {
    const { x: offsetX, y: offsetY } = state.drawOffset || getDrawParams();
    const scale = state.drawScale || state.originalScale * state.zoomLevel;
    return {
        x: (canvasPos.x - offsetX) / scale,
        y: (canvasPos.y - offsetY) / scale
    };
}

function findNearestLine(pos) {
    const threshold = Math.max(10, 5 / state.zoomLevel);  // 阈值随缩放调整
    const { x: offsetX, y: offsetY } = state.drawOffset || getDrawParams();
    const scale = state.drawScale || state.originalScale * state.zoomLevel;

    // 检查纵向切割线
    for (let i = 0; i < state.verticalLines.length; i++) {
        const lineX = offsetX + state.verticalLines[i] * scale;
        if (Math.abs(pos.x - lineX) < threshold) {
            return { type: 'vertical', index: i };
        }
    }

    // 检查横向切割线 - 只在鼠标所在的列中查找
    if (state.stripHorizontalLines && state.stripHorizontalLines.length > 0) {
        // 找到鼠标所在的列
        const imageX = (pos.x - offsetX) / scale;
        let currentStripIndex = -1;
        for (let i = 0; i < state.stripHorizontalLines.length; i++) {
            const strip = state.stripHorizontalLines[i];
            if (strip.x_start <= imageX && imageX <= strip.x_end) {
                currentStripIndex = i;
                break;
            }
        }

        if (currentStripIndex >= 0) {
            const strip = state.stripHorizontalLines[currentStripIndex];
            for (let i = 0; i < strip.horizontal_lines.length; i++) {
                const lineY = offsetY + strip.horizontal_lines[i] * scale;
                if (Math.abs(pos.y - lineY) < threshold) {
                    return {
                        type: 'horizontal',
                        stripIndex: currentStripIndex,
                        lineIndex: i,
                        yValue: strip.horizontal_lines[i]
                    };
                }
            }
        }
    } else {
        // 兼容旧数据
        for (let i = 0; i < state.horizontalLines.length; i++) {
            const lineY = offsetY + state.horizontalLines[i] * scale;
            if (Math.abs(pos.y - lineY) < threshold) {
                return { type: 'horizontal', index: i, yValue: state.horizontalLines[i] };
            }
        }
    }

    return null;
}

function addLineAt(type, position) {
    if (type === 'vertical') {
        const newX = Math.round(position);
        state.verticalLines.push(newX);
        state.verticalLines.sort((a, b) => a - b);

        // 更新 stripHorizontalLines 结构
        updateStripHorizontalLines();
    } else {
        const roundedY = Math.round(position);

        // 只添加到鼠标所在的那一列
        if (state.stripHorizontalLines && state.stripHorizontalLines.length > 0 && state.lastClickStripIndex !== undefined) {
            const strip = state.stripHorizontalLines[state.lastClickStripIndex];
            if (strip) {
                strip.horizontal_lines.push(roundedY);
                strip.horizontal_lines.sort((a, b) => a - b);
            }
        } else {
            // 兼容：添加到所有列
            state.horizontalLines.push(roundedY);
            state.horizontalLines.sort((a, b) => a - b);
            if (state.stripHorizontalLines) {
                state.stripHorizontalLines.forEach(strip => {
                    strip.horizontal_lines.push(roundedY);
                    strip.horizontal_lines.sort((a, b) => a - b);
                });
            }
        }
    }
    drawCanvas();
    updateUI();
    showToast(`已添加${type === 'vertical' ? '纵向' : '横向'}切割线`);
}

// 更新列结构（当竖向切割线变化时）
function updateStripHorizontalLines() {
    // 保存旧的列结构用于继承
    const oldStrips = state.stripHorizontalLines || [];

    console.log('更新列结构, 旧列数:', oldStrips.length, ', 新竖线数:', state.verticalLines.length);

    if (oldStrips.length === 0) {
        // 如果没有现有的列结构，创建默认的（只有边界线）
        const defaultHLines = [0, state.imageHeight];
        state.stripHorizontalLines = [];
        for (let i = 0; i < state.verticalLines.length - 1; i++) {
            state.stripHorizontalLines.push({
                strip_index: i,
                x_start: state.verticalLines[i],
                x_end: state.verticalLines[i + 1],
                horizontal_lines: [...defaultHLines]
            });
        }
        return;
    }

    // 为每个新的竖向区间找到重叠的原始列，合并其横向切割线
    const newStripHorizontalLines = [];
    for (let i = 0; i < state.verticalLines.length - 1; i++) {
        const xStart = state.verticalLines[i];
        const xEnd = state.verticalLines[i + 1];

        // 找到所有与新列重叠的原始列，合并它们的横向切割线
        const mergedHLines = new Set();
        mergedHLines.add(0);
        mergedHLines.add(state.imageHeight);

        for (const strip of oldStrips) {
            // 检查是否有重叠
            if (strip.x_start < xEnd && strip.x_end > xStart) {
                // 有重叠，合并横向切割线
                strip.horizontal_lines.forEach(y => mergedHLines.add(y));
            }
        }

        const hLines = Array.from(mergedHLines).sort((a, b) => a - b);

        console.log(`新列${i}: x=${xStart}-${xEnd}, 合并后横线数=${hLines.length}`);

        newStripHorizontalLines.push({
            strip_index: i,
            x_start: xStart,
            x_end: xEnd,
            horizontal_lines: hLines
        });
    }

    state.stripHorizontalLines = newStripHorizontalLines;
}

function deleteLine(lineInfo) {
    if (lineInfo.type === 'vertical') {
        if (lineInfo.index === 0 || lineInfo.index === state.verticalLines.length - 1) {
            showToast('无法删除边界线');
            return;
        }
        state.verticalLines.splice(lineInfo.index, 1);
        // 更新列结构
        updateStripHorizontalLines();
    } else {
        // 横向切割线 - 只从当前列中删除
        const yValue = lineInfo.yValue;
        if (yValue === 0 || yValue === state.imageHeight) {
            showToast('无法删除边界线');
            return;
        }

        // 只从当前列中删除
        if (lineInfo.stripIndex !== undefined && state.stripHorizontalLines) {
            const strip = state.stripHorizontalLines[lineInfo.stripIndex];
            if (strip) {
                const idx = strip.horizontal_lines.indexOf(yValue);
                if (idx !== -1) {
                    strip.horizontal_lines.splice(idx, 1);
                }
            }
        } else {
            // 兼容旧数据
            const idx = state.horizontalLines.indexOf(yValue);
            if (idx !== -1) {
                state.horizontalLines.splice(idx, 1);
            }
        }
    }
    drawCanvas();
    updateUI();
    showToast('已删除切割线');
}

function updateUI() {
    document.getElementById('vLineCount').textContent = state.verticalLines.length;
    document.getElementById('hLineCount').textContent = state.horizontalLines.length;
    const pieces = Math.max(0, (state.verticalLines.length - 1) * (state.horizontalLines.length - 1));
    document.getElementById('totalPieces').textContent = pieces;
}

async function saveCutLines() {
    if (!state.imageHash) return;

    showLoading('保存中...');

    console.log('保存切割线, boxes数量:', state.boxes ? state.boxes.length : 0);

    try {
        const response = await fetch('/api/save_cuts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hash: state.imageHash,
                vertical_lines: state.verticalLines,
                horizontal_lines: state.horizontalLines,
                strip_horizontal_lines: state.stripHorizontalLines,
                boxes: state.boxes
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast('切割线配置已保存');
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('保存失败: ' + error.message);
    }

    hideLoading();
}

async function applyCut() {
    if (!state.imageHash) return;

    showLoading('正在切割图片...');

    try {
        const response = await fetch('/api/apply_cuts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                hash: state.imageHash,
                vertical_lines: state.verticalLines,
                horizontal_lines: state.horizontalLines,
                strip_horizontal_lines: state.stripHorizontalLines
            })
        });
        const data = await response.json();

        if (data.success) {
            showToast(`切割完成！共 ${data.total_pieces} 个片段`);
            // 跳转到切割调整页面
            setTimeout(() => {
                window.location.href = '/adjust';
            }, 1000);
        } else {
            throw new Error(data.error);
        }
    } catch (error) {
        showToast('切割失败: ' + error.message);
    }

    hideLoading();
}

// 重置视图
function resetView() {
    state.zoomLevel = 1;
    state.panOffset = { x: 0, y: 0 };
    drawCanvas();
}

// 切换文本框显示
function toggleTextBoxes() {
    state.showTextBoxes = !state.showTextBoxes;
    drawCanvas();
}
