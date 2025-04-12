// 作文提交和状态更新处理
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('essayForm');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const processingStatus = document.getElementById('processingStatus');
    const statusText = document.getElementById('statusText');
    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // 显示加载动画
            loadingSpinner.style.display = 'block';
            processingStatus.classList.remove('d-none');
            
            try {
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // 更新状态显示
                    statusText.textContent = '作文正在批改中...';
                    
                    // 开始轮询批改状态
                    pollCorrectionStatus(result.essay_id);
                    
                    // 显示成功消息
                    showAlert('success', '作文已提交并开始批改，请稍候...');
                } else {
                    // 显示错误消息
                    showAlert('danger', result.message || '提交失败，请重试');
                    loadingSpinner.style.display = 'none';
                }
            } catch (error) {
                console.error('Error:', error);
                showAlert('danger', '提交时发生错误，请重试');
                loadingSpinner.style.display = 'none';
            }
        });
    }
    
    // 轮询批改状态
    async function pollCorrectionStatus(essayId) {
        try {
            const response = await fetch(`/api/v1/correction/essays/status/${essayId}`);
            
            // 检查HTTP状态码
            if (response.status === 401) {
                // 用户未登录或会话已过期
                const result = await response.json();
                statusText.textContent = '登录状态已过期';
                loadingSpinner.style.display = 'none';
                showAlert('warning', '登录状态已过期，请重新登录');
                
                // 如果返回了重定向URL，则跳转
                if (result.redirect) {
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 2000);
                }
                return;
            } else if (response.status === 404) {
                // 作文不存在
                const result = await response.json();
                statusText.textContent = '作文不存在';
                loadingSpinner.style.display = 'none';
                showAlert('danger', result.message || '找不到作文，请重试');
                return;
            } else if (!response.ok) {
                // 其他错误
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                switch(result.status) {
                    case 'pending':
                        statusText.textContent = '等待批改中...';
                        setTimeout(() => pollCorrectionStatus(essayId), 2000);
                        break;
                    case 'processing':
                        statusText.textContent = '正在处理中...';
                        setTimeout(() => pollCorrectionStatus(essayId), 2000);
                        break;
                    case 'correcting':
                        statusText.textContent = '正在批改中...';
                        setTimeout(() => pollCorrectionStatus(essayId), 2000);
                        break;
                    case 'completed':
                        statusText.textContent = '批改完成！';
                        loadingSpinner.style.display = 'none';
                        // 跳转到结果页面
                        showAlert('success', '批改已完成，正在跳转到结果页面...');
                        setTimeout(() => {
                            window.location.href = `/results/${essayId}`;
                        }, 1000);
                        break;
                    case 'failed':
                        statusText.textContent = '批改失败';
                        loadingSpinner.style.display = 'none';
                        showAlert('danger', '批改失败，请重试');
                        break;
                    default:
                        statusText.textContent = `未知状态: ${result.status}`;
                        setTimeout(() => pollCorrectionStatus(essayId), 2000);
                }
            } else {
                throw new Error(result.message || '获取状态失败');
            }
        } catch (error) {
            console.error('Error:', error);
            statusText.textContent = '获取状态失败';
            // 出错后延长轮询间隔
            setTimeout(() => pollCorrectionStatus(essayId), 5000);
        }
    }
    
    // 显示提示消息
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        const form = document.getElementById('essayForm');
        form.parentNode.insertBefore(alertDiv, form);
        
        // 5秒后自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }
    
    // 文件拖放处理
    const uploadArea = document.querySelector('.upload-area');
    const fileInput = document.getElementById('file');
    
    if (uploadArea && fileInput) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            uploadArea.classList.add('border-primary');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('border-primary');
        }
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            fileInput.files = files;
        }
    }
}); 