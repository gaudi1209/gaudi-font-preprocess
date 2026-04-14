/* 公共函数 */

// 显示提示消息
function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}

// 显示加载状态
function showLoading(message = '处理中...') {
    let loading = document.getElementById('loadingOverlay');
    if (!loading) {
        loading = document.createElement('div');
        loading.id = 'loadingOverlay';
        loading.className = 'loading';
        loading.innerHTML = `<div class="loading-text">${message}</div>`;
        document.body.appendChild(loading);
    } else {
        loading.querySelector('.loading-text').textContent = message;
        loading.style.display = 'flex';
    }
}

// 隐藏加载状态
function hideLoading() {
    const loading = document.getElementById('loadingOverlay');
    if (loading) {
        loading.style.display = 'none';
    }
}

// API 请求封装
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '请求失败');
        }
        return data;
    } catch (error) {
        console.error('API请求错误:', error);
        throw error;
    }
}
