// =====================================================================
// LOGIN PAGE SCRIPT
// =====================================================================

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
const API_REGISTER = `${API_BASE_URL}/register`;
const API_LOGIN = `${API_BASE_URL}/login`;

// Token management
function getToken() {
    return localStorage.getItem('access_token');
}

function setToken(token) {
    localStorage.setItem('access_token', token);
}

function isAuthenticated() {
    return getToken() !== null;
}

// Check if user is already logged in
function checkAndRedirect() {
    if (isAuthenticated()) {
        window.location.href = 'index.html';
    }
}

// Setup event listeners for tab switching
function setupTabListeners() {
    document.getElementById('tabLogin').addEventListener('click', () => {
        document.getElementById('loginForm').classList.remove('hidden');
        document.getElementById('registerForm').classList.add('hidden');
        document.getElementById('tabLogin').classList.add('border-indigo-600', 'bg-indigo-50');
        document.getElementById('tabLogin').classList.remove('border-transparent');
        document.getElementById('tabRegister').classList.remove('border-indigo-600', 'bg-indigo-50');
        document.getElementById('tabRegister').classList.add('border-transparent');
    });

    document.getElementById('tabRegister').addEventListener('click', () => {
        document.getElementById('loginForm').classList.add('hidden');
        document.getElementById('registerForm').classList.remove('hidden');
        document.getElementById('tabRegister').classList.add('border-indigo-600', 'bg-indigo-50');
        document.getElementById('tabRegister').classList.remove('border-transparent');
        document.getElementById('tabLogin').classList.remove('border-indigo-600', 'bg-indigo-50');
        document.getElementById('tabLogin').classList.add('border-transparent');
    });
}

// Setup login handler
function setupLoginHandler() {
    document.getElementById('btnLogin').addEventListener('click', async (e) => {
        e.preventDefault();
        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;
        const errorDiv = document.getElementById('loginError');
        const btn = document.getElementById('btnLogin');
        const spinner = document.getElementById('spinnerLogin');

        if (!username || !password) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = 'Vui lòng nhập tên đăng nhập và mật khẩu';
            return;
        }

        btn.disabled = true;
        spinner.classList.remove('hidden');

        try {
            const response = await fetch(API_LOGIN, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Đăng nhập thất bại');
            }

            const data = await response.json();
            setToken(data.access_token);
            
            errorDiv.classList.add('hidden');
            document.getElementById('loginUsername').value = '';
            document.getElementById('loginPassword').value = '';
            
            // Redirect to index
            window.location.href = 'index.html';
        } catch (err) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = err.message;
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });

    // Enter key support
    ['loginUsername', 'loginPassword'].forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('btnLogin').click();
        });
    });
}

// Setup register handler
function setupRegisterHandler() {
    document.getElementById('btnRegister').addEventListener('click', async (e) => {
        e.preventDefault();
        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const fullName = document.getElementById('regFullName').value.trim();
        const errorDiv = document.getElementById('registerError');
        const btn = document.getElementById('btnRegister');
        const spinner = document.getElementById('spinnerRegister');

        if (!username || !email || !password) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = 'Vui lòng nhập tên đăng nhập, email và mật khẩu';
            return;
        }

        if (password.length < 6) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = 'Mật khẩu phải có ít nhất 6 ký tự';
            return;
        }

        btn.disabled = true;
        spinner.classList.remove('hidden');

        try {
            const response = await fetch(API_REGISTER, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    full_name: fullName || null
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Đăng ký thất bại');
            }

            errorDiv.classList.add('hidden');
            
            // Auto login after registration
            const loginResponse = await fetch(API_LOGIN, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (loginResponse.ok) {
                const loginData = await loginResponse.json();
                setToken(loginData.access_token);
                
                document.getElementById('regUsername').value = '';
                document.getElementById('regEmail').value = '';
                document.getElementById('regPassword').value = '';
                document.getElementById('regFullName').value = '';
                
                // Redirect to index
                window.location.href = 'index.html';
            }
        } catch (err) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = err.message;
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });

    // Enter key support
    ['regUsername', 'regEmail', 'regPassword', 'regFullName'].forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('btnRegister').click();
        });
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAndRedirect();
    setupTabListeners();
    setupLoginHandler();
    setupRegisterHandler();
});
