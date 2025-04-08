// Constants
const API_BASE_URL = window.location.origin;
const TOKEN_KEY = 'parking_auth_token';
const REFRESH_TOKEN_KEY = 'parking_refresh_token';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000; // 1 second

// Variable to track if we're currently refreshing a token
let isRefreshingToken = false;
// Queue of requests to retry after token refresh
let refreshSubscribers = [];

// Function to add callbacks to the refresh queue
const subscribeTokenRefresh = (callback) => {
    refreshSubscribers.push(callback);
};

// Function to execute all the queued requests with the new token
const onTokenRefreshed = (token) => {
    refreshSubscribers.forEach(callback => callback(token));
    refreshSubscribers = [];
};

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

// Function to set auth token
function setAuthToken(token, refreshToken = null) {
    if (token) {
        localStorage.setItem(TOKEN_KEY, token);
    }
    if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
}

// Function to get auth token
function getAuthToken() {
    return localStorage.getItem(TOKEN_KEY);
}

// Function to get refresh token
function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

// Function to clear auth tokens
function clearAuthToken() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// Function to verify token
async function verifyToken() {
    const token = getAuthToken();
    if (!token) {
        return false;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/verify`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            return true;
        } else if (response.status === 401) {
            // Token expired, try to refresh
            return await refreshAccessToken();
        }
        return false;
    } catch (error) {
        console.error('Token verification failed:', error);
        return false;
    }
}

// Function to refresh access token
async function refreshAccessToken() {
    if (isRefreshingToken) {
        // If we're already refreshing, wait for the new token
        return new Promise((resolve) => {
            subscribeTokenRefresh((token) => {
                resolve(token);
            });
        });
    }

    isRefreshingToken = true;
    const refreshToken = getRefreshToken();

    if (!refreshToken) {
        isRefreshingToken = false;
        return false;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.token) {
                setAuthToken(data.token, data.refresh_token);
                onTokenRefreshed(data.token);
                return true;
            }
        }
        return false;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    } finally {
        isRefreshingToken = false;
    }
}

// Function to make API requests with retry mechanism
async function makeApiRequest(endpoint, options = {}, retryCount = 0) {
    const token = getAuthToken();
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : undefined
        }
    };

    const finalOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, finalOptions);

        if (response.ok) {
            const data = await response.json();
            return data;
        } else if (response.status === 401 && retryCount < MAX_RETRIES) {
            // Token expired, try to refresh
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                // Retry the request with new token
                return makeApiRequest(endpoint, options, retryCount + 1);
            }
            // If refresh failed, redirect to login
            window.location.href = '/login?expired=true';
            return null;
        } else {
            const error = await response.json();
            throw new Error(error.message || 'API request failed');
        }
    } catch (error) {
        console.error('API request failed:', error);
        if (retryCount < MAX_RETRIES) {
            // Wait before retrying
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * (retryCount + 1)));
            return makeApiRequest(endpoint, options, retryCount + 1);
        }
        throw error;
    }
}

// Function to handle login
async function login(username, password) {
    try {
        const response = await makeApiRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });

        if (response && response.token) {
            setAuthToken(response.token, response.refresh_token);
            showToast('Login successful', 'success');
            return true;
        }
        return false;
    } catch (error) {
        showToast(error.message || 'Login failed', 'error');
        return false;
    }
}

// Function to handle logout
function logout() {
    clearAuthToken();
    window.location.href = '/login';
}

// Function to check API health
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        return response.ok;
    } catch (error) {
        console.error('Health check failed:', error);
        return false;
    }
}

// Export functions to window.auth
window.auth = {
    setAuthToken,
    getAuthToken,
    clearAuthToken,
    verifyToken,
    login,
    logout,
    makeApiRequest,
    checkApiHealth
};

// Add token to all fetch requests
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    const token = localStorage.getItem(TOKEN_KEY);
    
    if (token) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    }
    
    return originalFetch(url, options)
        .then(response => {
            if (response.status === 401) {
                console.log(`Got 401 from fetch to ${url}`);
                clearAuthAndRedirect();
            }
            return response;
        })
        .catch(error => {
            console.error(`Network error for ${url}:`, error);
            showToast('Network error. Please check your connection.', 'error');
            throw error;
        });
};

// Function to show toast messages
function showToast(message, type = 'info') {
    if (typeof Toastify === 'function') {
        Toastify({
            text: message,
            duration: 3000,
            close: true,
            gravity: 'top',
            position: 'right',
            backgroundColor: type === 'error' ? '#e74c3c' : 
                            type === 'success' ? '#2ecc71' : '#3498db',
        }).showToast();
    } else {
        console.log(`Toast (${type}): ${message}`);
    }
}

// Function to handle API errors
function handleApiError(error, customMessage = 'An error occurred') {
    console.error('API Error:', error);
    
    if (error.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
        return;
    }
    
    let errorMessage = customMessage;
    
    if (error.message) {
        errorMessage = error.message;
    }
    
    showToast(errorMessage, 'error');
}

// Function to make API requests with retry
async function makeApiRequestWithRetry(url, method = 'GET', data = null, retries = 2) {
    try {
        // Show loading indicator if needed
        const showLoader = document.querySelector(`[data-api="${url}"]`);
        if (showLoader) {
            showLoader.classList.add('loading');
        }
        
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);
        
        // Remove loading indicator
        if (showLoader) {
            showLoader.classList.remove('loading');
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const error = new Error(errorData.message || `HTTP error! status: ${response.status}`);
            error.status = response.status;
            error.data = errorData;
            throw error;
        }
        
        return await response.json();
    } catch (error) {
        // Remove loading indicator
        const showLoader = document.querySelector(`[data-api="${url}"]`);
        if (showLoader) {
            showLoader.classList.remove('loading');
        }
        
        if (retries > 0 && (error.message.includes('network') || error.status >= 500)) {
            // Wait 1 second before retrying
            await new Promise(resolve => setTimeout(resolve, 1000));
            return makeApiRequestWithRetry(url, method, data, retries - 1);
        }
        
        handleApiError(error);
        throw error;
    }
}

// Function to check API health
async function checkApiHealth() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            showToast('API server is experiencing issues', 'error');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        showToast('Cannot connect to server', 'error');
    }
}

// Periodically check API health (every 30 seconds)
setInterval(checkApiHealth, 30000);

// Function to get dashboard data
async function getDashboardData() {
    try {
        const response = await makeApiRequest('/api/dashboard/stats/overview');
        return response.data;
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        return null;
    }
}

// Function to get activities
async function getActivities(page = 1, perPage = 5) {
    try {
        const response = await makeApiRequest(`/api/activities?page=${page}&per_page=${perPage}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching activities:', error);
        return null;
    }
}

// Function to get active parking sessions
async function getActiveSessions() {
    try {
        const response = await makeApiRequest('/api/parking-sessions/active');
        return response.data;
    } catch (error) {
        console.error('Error fetching active sessions:', error);
        return null;
    }
}

// Function to get daily reports
async function getDailyReports() {
    try {
        const response = await makeApiRequest('/api/reports/daily');
        return response.data;
    } catch (error) {
        console.error('Error fetching daily reports:', error);
        return null;
    }
}

// Function to get user profile
async function getUserProfile() {
    try {
        const response = await makeApiRequest('/api/auth/profile');
        return response.data;
    } catch (error) {
        console.error('Error fetching user profile:', error);
        return null;
    }
}

// Helper functions
function clearAuthAndRedirect() {
    console.log("Clearing auth and redirecting to login");
    clearAuthToken();
    redirectToLogin();
}

function redirectToLogin() {
    window.location.href = '/login';
} 