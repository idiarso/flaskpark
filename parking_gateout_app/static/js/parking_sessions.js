document.addEventListener('DOMContentLoaded', async function() {
    // Verify token first
    const isAuthenticated = await window.auth.verifyToken();
    if (!isAuthenticated) return;

    // Load initial data
    await loadParkingSessions();
    
    // Set up refresh button
    document.getElementById('refreshBtn')?.addEventListener('click', loadParkingSessions);
    
    // Set up create session button
    document.getElementById('createSessionBtn')?.addEventListener('click', createNewSession);
    
    // Auto refresh every 30 seconds
    setInterval(loadParkingSessions, 30000);
});

async function loadParkingSessions() {
    try {
        // Load active sessions
        const activeSessions = await window.auth.makeApiRequest('/api/parking-sessions/active');
        if (activeSessions) {
            updateActiveSessionsTable(activeSessions.data);
        }
        
        // Load recent sessions
        const recentSessions = await window.auth.makeApiRequest('/api/parking-sessions/recent');
        if (recentSessions) {
            updateRecentSessionsTable(recentSessions.data);
        }
        
        // Load available parking spaces
        const spaces = await window.auth.makeApiRequest('/api/parking-spaces/available');
        if (spaces) {
            updateParkingSpacesSelect(spaces.data);
        }
    } catch (error) {
        console.error('Error loading parking sessions:', error);
        showToast('Error loading parking sessions', 'error');
    }
}

function updateActiveSessionsTable(sessions) {
    const tbody = document.querySelector('#activeSessionsTable tbody');
    tbody.innerHTML = '';
    
    if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No active sessions</td></tr>';
        return;
    }
    
    sessions.forEach(session => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${session.ticket_number}</td>
            <td>${session.vehicle_plate}</td>
            <td>${formatDateTime(session.entry_time)}</td>
            <td>${formatDuration(session.duration)}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="endSession('${session.ticket_number}')">
                    <i class="fas fa-stop"></i> End Session
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateRecentSessionsTable(sessions) {
    const tbody = document.querySelector('#recentSessionsTable tbody');
    tbody.innerHTML = '';
    
    if (sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center">No recent sessions</td></tr>';
        return;
    }
    
    sessions.forEach(session => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${session.ticket_number}</td>
            <td>${session.vehicle_plate}</td>
            <td>${formatDateTime(session.entry_time)}</td>
            <td>${session.exit_time ? formatDateTime(session.exit_time) : '-'}</td>
            <td>${formatDuration(session.duration)}</td>
            <td>${formatCurrency(session.amount)}</td>
            <td><span class="badge bg-${getStatusColor(session.status)}">${session.status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

function updateParkingSpacesSelect(spaces) {
    const select = document.getElementById('parkingSpace');
    select.innerHTML = '<option value="">Select Space</option>';
    
    spaces.forEach(space => {
        const option = document.createElement('option');
        option.value = space.id;
        option.textContent = `${space.number} - ${space.type}`;
        select.appendChild(option);
    });
}

async function createNewSession() {
    const vehiclePlate = document.getElementById('vehiclePlate').value;
    const parkingSpaceId = document.getElementById('parkingSpace').value;
    
    if (!vehiclePlate || !parkingSpaceId) {
        showToast('Please fill in all fields', 'error');
        return;
    }
    
    try {
        const response = await window.auth.makeApiRequest('/api/parking-sessions', {
            method: 'POST',
            body: JSON.stringify({
                vehicle_plate: vehiclePlate,
                parking_space_id: parkingSpaceId
            })
        });
        
        if (response) {
            showToast('Session created successfully', 'success');
            document.getElementById('newSessionModal').querySelector('.btn-close').click();
            document.getElementById('newSessionForm').reset();
            loadParkingSessions();
        }
    } catch (error) {
        console.error('Error creating session:', error);
        showToast('Error creating session', 'error');
    }
}

async function endSession(ticketNumber) {
    if (!confirm('Are you sure you want to end this session?')) return;
    
    try {
        const response = await window.auth.makeApiRequest(`/api/parking-sessions/${ticketNumber}/end`, {
            method: 'POST'
        });
        
        if (response) {
            showToast('Session ended successfully', 'success');
            loadParkingSessions();
        }
    } catch (error) {
        console.error('Error ending session:', error);
        showToast('Error ending session', 'error');
    }
}

// Helper functions
function formatDateTime(dateTimeString) {
    return new Date(dateTimeString).toLocaleString();
}

function formatDuration(duration) {
    const hours = Math.floor(duration / 3600);
    const minutes = Math.floor((duration % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR'
    }).format(amount);
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'active':
            return 'success';
        case 'completed':
            return 'primary';
        case 'cancelled':
            return 'danger';
        default:
            return 'secondary';
    }
}

function showToast(message, type = 'info') {
    Toastify({
        text: message,
        duration: 3000,
        gravity: "top",
        position: "right",
        backgroundColor: type === 'error' ? '#dc3545' : 
                        type === 'success' ? '#28a745' : '#17a2b8',
    }).showToast();
} 