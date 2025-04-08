// Dashboard initialization
document.addEventListener('DOMContentLoaded', async function() {
    // Verify token first
    const isAuthenticated = await window.auth.verifyToken();
    if (!isAuthenticated) return;

    // Load dashboard data
    loadDashboardData();
    
    // Set up refresh button
    document.getElementById('refreshBtn').addEventListener('click', function() {
        loadDashboardData();
    });
    
    // Auto refresh every 30 seconds
    setInterval(loadDashboardData, 30000);
});

// Function to load all dashboard data
async function loadDashboardData() {
    try {
        // Load overview stats
        const overviewData = await window.auth.makeApiRequest('/api/dashboard/stats/overview');
        if (overviewData) {
            updateOverviewStats(overviewData.data);
        }
        
        // Load active sessions
        const sessionsData = await window.auth.makeApiRequest('/api/parking-sessions/active');
        if (sessionsData) {
            updateActiveSessions(sessionsData.data);
            document.getElementById('activeSessions').textContent = sessionsData.data.length;
        }
        
        // Load daily report
        const reportData = await window.auth.makeApiRequest('/api/reports/daily');
        if (reportData) {
            updateRevenueStats(reportData.data);
        }
        
        // Load recent activities
        const activitiesData = await window.auth.makeApiRequest('/api/activities?per_page=5');
        if (activitiesData) {
            updateRecentActivities(activitiesData.data.activities);
        }
        
        // Load vehicles count
        const vehiclesData = await window.auth.makeApiRequest('/api/vehicles');
        if (vehiclesData) {
            document.getElementById('totalVehicles').textContent = vehiclesData.data.total;
        }
        
        // Load hardware status
        const hardwareData = await window.auth.makeApiRequest('/api/hardware/status');
        if (hardwareData) {
            updateHardwareStatus(hardwareData);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// Function to update overview statistics
function updateOverviewStats(data) {
    document.getElementById('activeSessions').textContent = data.active_sessions;
    document.getElementById('availableSpaces').textContent = data.available_spaces;
}

// Function to update revenue statistics
function updateRevenueStats(data) {
    document.getElementById('todayRevenue').textContent = `$${data.total_revenue.toFixed(2)}`;
}

// Function to update active sessions display
function updateActiveSessions(sessions) {
    const tableBody = document.getElementById('activeSessionsTable');
    tableBody.innerHTML = '';
    
    if (sessions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center">No active sessions</td></tr>';
        return;
    }
    
    sessions.forEach(session => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${session.ticket_number}</td>
            <td>${session.vehicle_plate}</td>
            <td>${formatDateTime(session.entry_time)}</td>
            <td>${session.duration}</td>
        `;
        tableBody.appendChild(row);
    });
}

// Function to update recent activities
function updateRecentActivities(activities) {
    const activitiesList = document.getElementById('recentActivities');
    activitiesList.innerHTML = '';
    
    if (activities.length === 0) {
        activitiesList.innerHTML = '<div class="text-center text-muted">No recent activities</div>';
        return;
    }
    
    activities.forEach(activity => {
        const item = document.createElement('div');
        item.className = 'list-group-item';
        item.innerHTML = `
            <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1">${activity.action}</h6>
                <small class="text-muted">${formatRelativeTime(activity.created_at)}</small>
            </div>
            <p class="mb-1">${activity.details}</p>
            <small class="text-${getStatusColor(activity.status)}">${activity.status}</small>
        `;
        activitiesList.appendChild(item);
    });
}

// Function to update hardware status
function updateHardwareStatus(data) {
    const hardwareTable = document.getElementById('hardware-status');
    if (!hardwareTable) return;

    const tbody = hardwareTable.getElementsByTagName('tbody')[0];
    tbody.innerHTML = '';

    if (!data.devices || data.devices.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">No hardware devices found</td></tr>';
        return;
    }

    data.devices.forEach(device => {
        const row = tbody.insertRow();
        row.innerHTML = `
            <td>${device.device_type}</td>
            <td>${device.location}</td>
            <td><span class="badge bg-${device.status === 'online' ? 'success' : 'danger'}">${device.status}</span></td>
            <td>${formatRelativeTime(new Date(device.last_ping))}</td>
        `;
    });
}

// Helper function to format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Helper function to format date and time
function formatDateTime(dateTimeString) {
    const date = new Date(dateTimeString);
    return date.toLocaleString();
}

// Helper function to format duration
function formatDuration(ms) {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else {
        return `${minutes}m`;
    }
}

// Helper function to format relative time
function formatRelativeTime(dateTimeString) {
    const date = new Date(dateTimeString);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) {
        return `${minutes}m ago`;
    }
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) {
        return `${hours}h ago`;
    }
    
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}

// Helper function to get status color
function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'success':
            return 'success';
        case 'error':
            return 'danger';
        case 'warning':
            return 'warning';
        default:
            return 'info';
    }
}

// Function to show toast notifications
function showToast(message, type = 'info') {
    Toastify({
        text: message,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#17a2b8',
    }).showToast();
} 