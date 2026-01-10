// Frontend API Configuration
// File: UI/assets/js/api-config.js

const API_CONFIG = {
    // Development
    DEV: {
        baseURL: 'http://localhost:5000',
        timeout: 30000
    },
    
    // Production (GKE)
    PROD: {
        baseURL: 'http://34.87.54.108.nip.io/api',
        timeout: 30000
    },
    
    // Determine environment
    environment: window.location.hostname === 'localhost' ? 'DEV' : 'PROD'
};

// Get current API config
function getApiConfig() {
    return API_CONFIG[API_CONFIG.environment];
}

// API Helper function
async function apiCall(endpoint, method = 'GET', body = null) {
    const config = getApiConfig();
    const url = config.baseURL + endpoint;
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        timeout: config.timeout
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token expired, redirect to login
                localStorage.removeItem('access_token');
                window.location.href = '/pages/login.html';
                return null;
            }
            throw new Error(`API Error: ${response.status} ${response.statusText}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Call Error:', error);
        throw error;
    }
}

// Auth APIs
const AuthAPI = {
    register: async (username, email, password, fullName) => {
        return apiCall('/register', 'POST', {
            username,
            email,
            password,
            full_name: fullName
        });
    },
    
    login: async (username, password) => {
        const config = getApiConfig();
        const url = config.baseURL + '/login';
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: new URLSearchParams({
                username,
                password
            })
        });
        
        if (!response.ok) {
            throw new Error(`Login failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        localStorage.setItem('access_token', data.access_token);
        return data;
    },
    
    logout: async () => {
        localStorage.removeItem('access_token');
        return true;
    },
    
    getProfile: () => apiCall('/profile', 'GET')
};

// Prediction APIs
const PredictionAPI = {
    predict: (income, score, contactStatus) => 
        apiCall('/predict', 'POST', {
            income,
            score,
            contact_status: contactStatus
        }),
    
    processLoans: (file) => {
        const config = getApiConfig();
        const url = config.baseURL + '/process-loans';
        const formData = new FormData();
        formData.append('file', file);
        
        return fetch(url, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: formData
        }).then(r => r.json());
    }
};

// Session APIs
const SessionAPI = {
    getSessionResults: (sessionId) => 
        apiCall(`/sessions/${sessionId}/results`, 'GET')
};

// Admin APIs
const AdminAPI = {
    getUsers: () => apiCall('/admin/users', 'GET'),
    
    createUser: (username, email, password, fullName, role) =>
        apiCall('/admin/users', 'POST', {
            username,
            email,
            password,
            full_name: fullName,
            role
        }),
    
    deleteUser: (userId) => 
        apiCall(`/admin/users/${userId}`, 'DELETE')
};

// Export APIs
window.API = {
    AuthAPI,
    PredictionAPI,
    SessionAPI,
    AdminAPI,
    getApiConfig
};
