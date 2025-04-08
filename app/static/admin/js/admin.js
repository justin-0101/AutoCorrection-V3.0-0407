/**
 * Admin Backend Script
 */

// Global variables
const API_BASE_URL = '/api/v1/admin';
let currentUser = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Admin JS loaded');
    checkCurrentUser();
    
    // Load dashboard data if on dashboard page
    const dashboardContent = document.getElementById('dashboard-content');
    if (dashboardContent) {
        loadDashboardData();
    }
});

/**
 * Show message to user
 * @param {string} message - Message content
 * @param {string} type - Message type (success, error, warning, info)
 */
function showMessage(message, type = 'info') {
    // Try to use Bootstrap toast if available
    const toastEl = document.getElementById('liveToast');
    if (toastEl && window.bootstrap) {
        const toastBody = toastEl.querySelector('.toast-body');
        if (toastBody) {
            toastBody.textContent = message;
            toastEl.className = `toast bg-${type} text-white`;
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
            return;
        }
    }
    
    // Fallback to alert
    alert(message);
}

/**
 * Check current user info and permissions
 */
async function checkCurrentUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/users/me`);
        
        if (response.status === 401) {
            showMessage('Session expired. Redirecting to login...', 'warning');
            setTimeout(() => {
                window.location.href = '/login?redirect=/admin';
            }, 1500);
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to get user info');
        }
        
        const data = await response.json();
        currentUser = data.user;
        
        if (!currentUser?.is_admin) {
            showMessage('No admin privileges', 'error');
            window.location.href = '/';
            return;
        }
    } catch (error) {
        console.error('Error checking user:', error);
        showMessage('Failed to verify user permissions', 'error');
    }
}

/**
 * Load dashboard data
 */
async function loadDashboardData() {
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard`);
        
        if (!response.ok) {
            throw new Error('Failed to load dashboard data');
        }
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.message || 'Data fetch failed');
        }
        
        const data = result.data;
        
        // Update dashboard elements safely
        const updateElement = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
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
        
        console.log('Dashboard data loaded');
        
    } catch (error) {
        console.error('Dashboard load error:', error);
        showMessage('Failed to load dashboard data: ' + error.message, 'error');
    }
} 