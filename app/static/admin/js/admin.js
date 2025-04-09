/**
 * Admin Backend Script
 */

// Global variables
const API_BASE_URL = '/api/v1/admin';
let currentUser = null;

// 全局错误处理
window.onerror = function(message, source, lineno, colno, error) {
    console.error("管理后台JS错误:", message, "源:", source, "行号:", lineno);
    // 防止错误冒泡
    return true;
};

// 处理未捕获的Promise异常
window.addEventListener('unhandledrejection', function(event) {
    console.error('未处理的Promise错误:', event.reason);
    event.preventDefault();
});

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('管理后台JS已加载');
    
    // 安全地尝试初始化
    try {
        // 轻量级用户检查 - 出错也不要阻止页面加载
        checkCurrentUser().catch(err => {
            console.warn('用户检查失败, 但页面将继续加载:', err);
        });
        
        // 轻量级加载仪表盘数据 - 采用非阻断式方法
        const dashboardContent = document.getElementById('dashboard-content');
        if (dashboardContent) {
            loadDashboardData().catch(err => {
                console.warn('加载仪表盘数据失败:', err);
                showMessage('加载数据失败，请刷新页面重试', 'warning');
            });
        }
    } catch (e) {
        console.error('初始化过程出错:', e);
    }
});

/**
 * Show message to user
 * @param {string} message - Message content
 * @param {string} type - Message type (success, error, warning, info)
 */
function showMessage(message, type = 'info') {
    try {
        // Try to use Bootstrap toast if available
        const toastEl = document.getElementById('liveToast');
        if (toastEl && window.bootstrap && window.bootstrap.Toast) {
            const toastBody = toastEl.querySelector('.toast-body');
            if (toastBody) {
                toastBody.textContent = message;
                toastEl.className = `toast bg-${type} text-white`;
                const toast = new window.bootstrap.Toast(toastEl);
                toast.show();
                return;
            }
        }
        
        // Fallback to alert
        console.log(message);
        
        // 创建一个临时alert元素，而不是使用alert()弹窗
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // 尝试添加到页面
        const adminContent = document.querySelector('.admin-content');
        if (adminContent) {
            adminContent.prepend(alertDiv);
            // 5秒后自动消失
            setTimeout(() => {
                alertDiv.classList.remove('show');
                setTimeout(() => alertDiv.remove(), 150);
            }, 5000);
        }
    } catch (e) {
        // 最终的后备方案 - 控制台输出
        console.warn('显示消息失败:', message, '类型:', type);
    }
}

/**
 * Check current user info and permissions
 */
async function checkCurrentUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/me`);
        
        if (response.status === 401) {
            showMessage('会话已过期，请重新登录', 'warning');
            // 延迟重定向，确保消息显示
            setTimeout(() => {
                window.location.href = '/login?redirect=/admin';
            }, 2000);
            return;
        }

        if (!response.ok) {
            throw new Error('获取用户信息失败');
        }
        
        const data = await response.json();
        currentUser = data.user;
        
        if (!currentUser?.is_admin) {
            showMessage('没有管理员权限', 'error');
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
            return;
        }
    } catch (error) {
        console.error('检查用户错误:', error);
        // 不要显示破坏性的错误消息，使用更温和的警告
        // showMessage('验证用户权限失败', 'error');
    }
}

/**
 * Load dashboard data
 */
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard`);
        
        if (!response.ok) {
            throw new Error('加载仪表盘数据失败');
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || '数据获取失败');
        }
        
        const data = result.data || {};
        
        // Update dashboard elements safely
        const updateElement = (id, value) => {
            try {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            } catch (e) {
                console.warn(`更新元素 ${id} 失败:`, e);
            }
        };
        
        // Update stats if data exists
        if (data.users) {
            updateElement('total-users', data.users.total);
            updateElement('premium-users', data.users.premium || 0);
        }
        
        if (data.essays) {
            updateElement('total-essays', data.essays.total);
            updateElement('pending-essays', data.essays.pending || 0);
        }
        
        if (data.corrections) {
            updateElement('total-corrections', data.corrections.total);
            updateElement('pending-corrections', data.corrections.pending || 0);
        }
        
        console.log('仪表盘数据已加载');
        
    } catch (error) {
        console.error('仪表盘加载错误:', error);
        // 不阻止页面运行，只在控制台记录错误
    }
} 