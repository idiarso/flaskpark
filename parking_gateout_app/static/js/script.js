// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0
    }).format(amount);
}

function formatDateTime(dateStr) {
    return new Date(dateStr).toLocaleString('id-ID');
}

function showError(message, elementId = 'errorMessage') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

function hideError(elementId = 'errorMessage') {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

// Login form handling
const loginForm = document.getElementById('loginForm');
if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            if (data.status === 'success') {
                localStorage.setItem('token', data.data.token);
                window.location.href = '/dashboard';
            } else {
                showError(data.message, 'loginMessage');
            }
        } catch (error) {
            showError('Login failed. Please try again.');
        }
    });
}

// Dashboard functionality
async function loadActiveVehicles() {
    const table = document.getElementById('activeVehiclesTable');
    if (!table) return;

    try {
        const response = await fetch('/api/parking-sessions/active', {
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        });

        const data = await response.json();
        if (data.status === 'success') {
            const tbody = table.querySelector('tbody');
            tbody.innerHTML = data.data.map(vehicle => `
                <tr>
                    <td>${vehicle.plateNumber}</td>
                    <td>${formatDateTime(vehicle.entryTime)}</td>
                    <td>${vehicle.parkingSpaceId}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showError('Failed to load active vehicles');
    }
}

// Exit form handling
const exitForm = document.getElementById('exitForm');
if (exitForm) {
    const calculateFeeBtn = document.getElementById('calculateFeeBtn');
    const processPaymentBtn = document.getElementById('processPaymentBtn');
    const resultSection = document.getElementById('resultSection');

    calculateFeeBtn.addEventListener('click', async () => {
        const ticketNumber = document.getElementById('ticketNumber').value;
        hideError();

        try {
            const response = await fetch('/api/parking-sessions/exit', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ ticketNumber })
            });

            const data = await response.json();
            if (data.status === 'success') {
                document.getElementById('vehicleDetails').innerHTML = `
                    Ticket: ${data.data.ticketNumber}<br>
                    Duration: ${data.data.duration}
                `;
                document.getElementById('totalFee').textContent = `Total Fee: ${formatCurrency(data.data.fee)}`;
                resultSection.style.display = 'block';
            } else {
                showError(data.message);
            }
        } catch (error) {
            showError('Failed to calculate fee');
        }
    });

    processPaymentBtn.addEventListener('click', async () => {
        const ticketNumber = document.getElementById('ticketNumber').value;
        const paymentMethod = document.getElementById('paymentMethod').value;

        try {
            const response = await fetch('/api/payments/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({ ticketNumber, paymentMethod })
            });

            const data = await response.json();
            if (data.status === 'success') {
                document.getElementById('paymentMessage').innerHTML = `
                    <div class="success-message">
                        Payment processed successfully<br>
                        Transaction ID: ${data.data.transactionId}
                    </div>
                `;
            } else {
                showError(data.message, 'paymentMessage');
            }
        } catch (error) {
            showError('Failed to process payment', 'paymentMessage');
        }
    });
}

// Reports functionality
const reportForm = document.getElementById('reportForm');
if (reportForm) {
    const reportType = document.getElementById('reportType');
    const reportFields = {
        daily: document.getElementById('dailyFields'),
        monthly: document.getElementById('monthlyFields'),
        custom: document.getElementById('customFields')
    };

    // Show/hide report fields based on selection
    reportType.addEventListener('change', () => {
        Object.values(reportFields).forEach(field => field.style.display = 'none');
        reportFields[reportType.value].style.display = 'block';
    });

    document.getElementById('generateReportBtn').addEventListener('click', async () => {
        hideError();
        const type = reportType.value;
        let url, method, body;

        switch (type) {
            case 'daily':
                const date = document.getElementById('dailyDate').value;
                url = `/api/reports/daily?date=${date}`;
                method = 'GET';
                break;
            case 'monthly':
                const month = document.getElementById('monthSelect').value;
                const year = document.getElementById('yearSelect').value;
                url = `/api/reports/monthly?month=${month}&year=${year}`;
                method = 'GET';
                break;
            case 'custom':
                url = '/api/reports/generate';
                method = 'POST';
                body = JSON.stringify({
                    start_date: document.getElementById('startDate').value,
                    end_date: document.getElementById('endDate').value
                });
                break;
        }

        try {
            const response = await fetch(url, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body
            });

            const data = await response.json();
            if (data.status === 'success') {
                displayReportResults(data.data);
            } else {
                showError(data.message);
            }
        } catch (error) {
            showError('Failed to generate report');
        }
    });
}

function displayReportResults(data) {
    const tbody = document.querySelector('#reportTable tbody');
    const reportResults = document.getElementById('reportResults');
    
    if (data.length === 0) {
        showError('No data available for this period');
        reportResults.style.display = 'none';
        return;
    }

    let totalVehicles = 0;
    let totalRevenue = 0;

    tbody.innerHTML = data.map(row => {
        totalVehicles += row.vehicles;
        totalRevenue += row.revenue;
        return `
            <tr>
                <td>${row.date}</td>
                <td>${row.vehicles}</td>
                <td>${formatCurrency(row.revenue)}</td>
                <td>${row.avgDuration || '-'}</td>
            </tr>
        `;
    }).join('');

    document.getElementById('totalVehicles').textContent = totalVehicles;
    document.getElementById('totalRevenue').textContent = formatCurrency(totalRevenue);
    reportResults.style.display = 'block';
}

// Initialize dashboard if on dashboard page
if (document.getElementById('activeVehiclesTable')) {
    loadActiveVehicles();
    // Refresh active vehicles list every 30 seconds
    setInterval(loadActiveVehicles, 30000);
}
