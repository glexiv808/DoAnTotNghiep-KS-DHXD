// =====================================================================
// 0. API CONFIGURATION & TOKEN MANAGEMENT
// =====================================================================
// const API_BASE_URL = 'http://34.87.54.108.nip.io';
const API_BASE_URL = 'http://127.0.0.1:8000';
const API_URL = `${API_BASE_URL}/predict`;
const API_REGISTER = `${API_BASE_URL}/register`;
const API_LOGIN = `${API_BASE_URL}/login`;
const API_LOGOUT = `${API_BASE_URL}/logout`;

// Token management
function getToken() {
    return localStorage.getItem('access_token');
}

function setToken(token) {
    localStorage.setItem('access_token', token);
}

function clearToken() {
    localStorage.removeItem('access_token');
}

function isAuthenticated() {
    return getToken() !== null;
}

function getAuthHeader() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// =====================================================================
// 1. CẤU HÌNH HỆ THỐNG
// =====================================================================
const SCALER_CONFIG = {
    person_age: { mean: 27.76417777777778, scale: 6.045041043106284 },
    person_income: { mean: 80319.05322222222, scale: 80421.60504361271 },
    person_emp_exp: { mean: 5.410333333333333, scale: 6.0634647136215225 },
    loan_amnt: { mean: 9583.157555555556, scale: 6314.816524743712 },
    loan_int_rate: { mean: 11.006605777777779, scale: 2.9787751821717214 },
    loan_percent_income: { mean: 0.1397248888888889, scale: 0.08721133898301228 },
    cb_person_cred_hist_length: { mean: 5.8674888888888885, scale: 3.8796587371240796 },
    credit_score: { mean: 632.6087555555556, scale: 50.43530459912891 },
};

const CAT_MAP = {
    person_gender: { 'female': 0, 'male': 1, 'nu': 0, 'nam': 1 },
    person_education: { 'high school': 3, 'bachelor': 1,  'master': 4, 'doctorate': 2 },
    person_home_ownership: { 'mortgage': 0, 'own': 2, 'rent': 3},
    loan_intent: { 'education': 1, 'medical': 3, 'venture': 5, 'personal': 4, 'debtconsolidation': 0, 'homeimprovement': 2 },
    previous_loan_defaults_on_file: { 'no': 0, 'yes': 1, 'khong': 0, 'co': 1 }
};

const FIELD_LIST = [
    'person_age', 'person_gender', 'person_education', 'person_income',
    'person_emp_exp', 'person_home_ownership', 'loan_amnt', 'loan_intent',
    'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length',
    'credit_score', 'previous_loan_defaults_on_file'
];

// =====================================================================
// 2. LOGIN/REGISTER MODAL MANAGEMENT
// =====================================================================
function initAuthUI() {
    if (isAuthenticated()) {
        document.getElementById('loginModal').classList.add('hidden');
        updateUserInfo();
        setupLogoutListener();  // Gắn logout listener khi đã xác thực
    } else {
        document.getElementById('loginModal').classList.remove('hidden');
        setupAuthListeners();
    }
}

function updateUserInfo() {
    // Fetch current user info
    fetch(`${API_BASE_URL}/users/me`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader()
        }
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById('currentUser').textContent = data.username;
        document.getElementById('userInfo').classList.remove('hidden');
        document.getElementById('authStatus').classList.add('hidden');
        setupLogoutListener();  // Gắn logout listener sau khi cập nhật user info
    })
    .catch(() => {
        clearToken();
        initAuthUI();
    });
}

// Hàm riêng để setup logout listener
function setupLogoutListener() {
    const btnLogout = document.getElementById('btnLogout');
    if (!btnLogout) return;

    // Xóa event listener cũ trước khi thêm cái mới
    const newBtnLogout = btnLogout.cloneNode(true);
    btnLogout.parentNode.replaceChild(newBtnLogout, btnLogout);

    newBtnLogout.addEventListener('click', async (e) => {
        e.preventDefault();
        e.stopPropagation();

        try {
            const response = await fetch(API_LOGOUT, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                }
            });

            if (response.ok) {
                console.log('Logged out successfully');
            }
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            clearToken();
            initAuthUI();
        }
    });
}

function setupAuthListeners() {
    // Tab switching
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

    // Login handler
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
            
            initAuthUI();
        } catch (err) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = err.message;
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });

    // Register handler
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
                
                initAuthUI();
            }
        } catch (err) {
            errorDiv.classList.remove('hidden');
            errorDiv.textContent = err.message;
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });

    // Enter key for inputs
    ['loginUsername', 'loginPassword'].forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('btnLogin').click();
        });
    });

    ['regUsername', 'regEmail', 'regPassword', 'regFullName'].forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') document.getElementById('btnRegister').click();
        });
    });
}

// =====================================================================
// 3. DATA PREPROCESSING
// =====================================================================
function preprocessValue(key, value) {
    if (CAT_MAP[key]) {
        const normalizedVal = String(value).toLowerCase().trim();
        if (CAT_MAP[key][normalizedVal] !== undefined) {
            value = CAT_MAP[key][normalizedVal];
        }
    }

    let numVal = Number(value);
    if (isNaN(numVal)) numVal = 0;

    const config = SCALER_CONFIG[key];
    if (config) {
        if (config.scale === 0 || config.scale < 1e-8) {
            return 0;
        }
        return (numVal - config.mean) / config.scale;
    }
    return numVal;
}

// =====================================================================
// 4. SINGLE PREDICTION
// =====================================================================
const singleForm = document.getElementById('singleForm');
if (singleForm) {
    singleForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        
        if (!isAuthenticated()) {
            alert('Vui lòng đăng nhập trước');
            return;
        }

        const btn = document.getElementById('btnSingle');
        const spinner = document.getElementById('spinnerSingle');
        const resBox = document.getElementById('resultSingle');

        btn.disabled = true;
        spinner.classList.remove('hidden');
        resBox.classList.add('hidden');

        const processedData = {};
        FIELD_LIST.forEach(field => {
            const rawVal = document.getElementById(field).value;
            processedData[field] = preprocessValue(field, rawVal);
        });

        const vectorPayload = FIELD_LIST.map(field => processedData[field]);
        const bodyToSend = vectorPayload;

        console.log("Vector gửi đi:", bodyToSend);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                },
                body: JSON.stringify(bodyToSend)
            });

            if (response.status === 401) {
                clearToken();
                initAuthUI();
                throw new Error('Token hết hạn, vui lòng đăng nhập lại');
            }

            if (!response.ok) throw new Error("Lỗi kết nối Server API");

            const data = await response.json();
            console.log("Server trả về:", data);

            let resultValue = 0;
            if (data.prediction && Array.isArray(data.prediction)) {
                resultValue = data.prediction[0];
            }

            resBox.classList.remove('hidden');

            if (resultValue == 1) {
                resBox.className = "mt-4 p-4 rounded-lg border-2 text-center bg-green-50 border-green-500 text-green-800";
                document.getElementById('resTitleSingle').innerText = "Có thể trả nợ";
                document.getElementById('resMsgSingle').innerText = "Rủi ro thấp (Prediction: 1)";
            } else {
                resBox.className = "mt-4 p-4 rounded-lg border-2 text-center bg-red-50 border-red-500 text-red-800";
                document.getElementById('resTitleSingle').innerText = "Không trả được nợ";
                document.getElementById('resMsgSingle').innerText = "Rủi ro cao (Prediction: 0)";
            }
        } catch (err) {
            alert("Lỗi: " + err.message);
        } finally {
            btn.disabled = false;
            spinner.classList.add('hidden');
        }
    });
}

// =====================================================================
// 5. FORM VALIDATION
// =====================================================================
function validateCreditScore(value) {
    const score = Number(value);
    if (isNaN(score)) return false;
    return score >= 300 && score <= 850;
}

function setupSingleFormValidation() {
    const fields = FIELD_LIST;
    const form = document.getElementById('singleForm');
    const submitButton = document.getElementById('btnSingle');
    const creditScoreInput = document.getElementById('credit_score');
    const creditScoreError = document.getElementById('credit_score_error');

    if (!form || !submitButton) return;

    // Prevent invalid credit score input directly at the field level
    if (creditScoreInput) {
        creditScoreInput.addEventListener('blur', function() {
            if (this.value) {
                const score = Number(this.value);
                if (score < 300) {
                    this.value = 300;
                } else if (score > 850) {
                    this.value = 850;
                }
            }
            // Trigger input event to update validation
            this.dispatchEvent(new Event('input', { bubbles: true }));
        });

        creditScoreInput.addEventListener('input', function() {
            if (this.value && !validateCreditScore(this.value)) {
                creditScoreError.classList.remove('hidden');
            } else {
                creditScoreError.classList.add('hidden');
            }
            checkFormValidity();
        });

        // Also prevent invalid paste
        creditScoreInput.addEventListener('paste', function(e) {
            setTimeout(() => {
                if (this.value) {
                    const score = Number(this.value);
                    if (score < 300) {
                        this.value = 300;
                    } else if (score > 850) {
                        this.value = 850;
                    }
                }
                this.dispatchEvent(new Event('input', { bubbles: true }));
            }, 0);
        });
    }

    function checkFormValidity() {
        if (!isAuthenticated()) {
            submitButton.disabled = true;
            return;
        }

        let allValid = true;
        for (const fieldId of fields) {
            const inputElement = document.getElementById(fieldId);
            if (!inputElement || String(inputElement.value).trim() === '') {
                allValid = false;
                break;
            }
            // Additional validation for credit_score
            if (fieldId === 'credit_score' && inputElement.value && !validateCreditScore(inputElement.value)) {
                allValid = false;
                break;
            }
        }

        submitButton.disabled = !allValid;

        if (allValid) {
            submitButton.classList.replace('bg-slate-300', 'bg-indigo-600');
            submitButton.classList.add('hover:bg-indigo-700');
        } else {
            submitButton.classList.replace('bg-indigo-600', 'bg-slate-300');
            submitButton.classList.remove('hover:bg-indigo-700');
        }
    }

    form.addEventListener('input', checkFormValidity);
    form.addEventListener('change', checkFormValidity);

    checkFormValidity();
}

setupSingleFormValidation();

// =====================================================================
// 6. BATCH PROCESSING
// =====================================================================
let batchData = [];
const fileInput = document.getElementById('excelFile');
const btnBatch = document.getElementById('btnBatch');
const fileInfo = document.getElementById('fileInfo');

if (fileInput) {
    fileInput.addEventListener('change', function (e) {
        const file = e.target.files[0];
        if (!file) return;

        fileInfo.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span> ${file.name}`;
        btnBatch.disabled = false;
        btnBatch.classList.remove('bg-slate-300', 'cursor-not-allowed');
        btnBatch.classList.add('bg-emerald-600', 'hover:bg-emerald-700', 'text-white');

        const reader = new FileReader();
        reader.onload = function (e) {
            const data = new Uint8Array(e.target.result);
            const workbook = XLSX.read(data, { type: 'array' });
            const firstSheet = workbook.SheetNames[0];
            batchData = XLSX.utils.sheet_to_json(workbook.Sheets[firstSheet]);
        };
        reader.readAsArrayBuffer(file);
    });
}

async function processBatch() {
    if (!isAuthenticated()) {
        alert('Vui lòng đăng nhập trước');
        return;
    }

    if (batchData.length === 0) return alert("File không có dữ liệu!");

    const spinner = document.getElementById('spinnerBatch');
    const tbody = document.getElementById('resultTableBody');

    btnBatch.disabled = true;
    spinner.classList.remove('hidden');
    tbody.innerHTML = "";

    let count = 0;
    for (const row of batchData) {
        count++;
        const name = row['Ho_ten'] || row['Name'] || row['HO_TEN'] || row['Full Name'] || `Hồ sơ #${count}`;

        // Validate credit_score before processing
        const creditScoreKey = Object.keys(row).find(k => k.toLowerCase() === 'credit_score');
        const creditScoreVal = creditScoreKey ? row[creditScoreKey] : 0;
        
        if (creditScoreVal && !validateCreditScore(creditScoreVal)) {
            const tr = document.createElement('tr');
            tr.className = "hover:bg-slate-50 transition border-b border-gray-100 bg-red-50";
            tr.innerHTML = `
                <td class="px-5 py-4 text-sm text-gray-500 text-center">${count}</td>
                <td class="px-5 py-4 text-sm font-bold text-gray-800">${name}</td>
                <td class="px-5 py-4 text-sm text-gray-600">-</td>
                <td class="px-5 py-4 text-sm text-center text-gray-600">${creditScoreVal}</td>
                <td class="px-5 py-4 text-sm text-center"><span class="px-2 py-1 text-red-900 bg-red-200 rounded text-xs">Invalid Score</span></td>
                <td class="px-5 py-4 text-sm text-center">-</td>
            `;
            tbody.appendChild(tr);
            continue;
        }

        const processedData = {};
        FIELD_LIST.forEach(key => {
            const rowKey = Object.keys(row).find(k => k.toLowerCase() === key.toLowerCase());
            const rawVal = rowKey ? row[rowKey] : 0;
            processedData[key] = preprocessValue(key, rawVal);
        });

        const vectorPayload = FIELD_LIST.map(key => processedData[key]);
        const bodyToSend = vectorPayload;

        let statusHtml = `<span class="text-gray-400 text-xs italic">Đang xử lý...</span>`;
        let displayStatus = -1;

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                },
                body: JSON.stringify(bodyToSend)
            });

            if (res.status === 401) {
                clearToken();
                initAuthUI();
                alert('Token hết hạn, vui lòng đăng nhập lại');
                break;
            }

            if (res.ok) {
                const data = await res.json();
                if (data.prediction && Array.isArray(data.prediction)) {
                    displayStatus = data.prediction[0];
                }
            }
        } catch (e) {
            console.error(e);
        }

        if (displayStatus == 1) {
            statusHtml = `<span class="px-2 py-1 font-bold text-green-900 bg-green-200 rounded-full text-xs">Rủi ro thấp</span>`;
        } else if (displayStatus == 0) {
            statusHtml = `<span class="px-2 py-1 font-bold text-red-900 bg-red-200 rounded-full text-xs">Rủi ro cao</span>`;
        } else {
            statusHtml = `<span class="px-2 py-1 text-gray-500 bg-gray-200 rounded text-xs">Lỗi API</span>`;
        }

        const displayIncome = row['person_income'] || row['Person_Income'] || 0;
        const displayScore = row['credit_score'] || row['Credit_Score'] || '-';

        // Tạo unique ID cho mỗi row
        const rowId = `row-${count}`;

        const contactStatusHtml = `
            <select class="contact-status-select px-2 py-1 border border-gray-300 rounded text-xs bg-white cursor-pointer hover:border-indigo-500 transition" data-row-id="${rowId}" data-row-number="${count}" data-name="${name}">
                <option value="">-- Chọn --</option>
                <option value="da_lien_lac" style="background-color: #dcfce7; color: #166534;">✓ Đã liên lạc</option>
                <option value="chua_lien_lac" style="background-color: #fef3c7; color: #92400e;">○ Chưa liên lạc</option>
                <option value="khong_lien_lac_duoc" style="background-color: #fee2e2; color: #991b1b;">✕ Không liên lạc được</option>
            </select>
        `;

        const tr = document.createElement('tr');
        tr.id = rowId;
        tr.className = "hover:bg-slate-50 transition border-b border-gray-100";
        tr.innerHTML = `
            <td class="px-5 py-4 text-sm text-gray-500 text-center">${count}</td>
            <td class="px-5 py-4 text-sm font-bold text-gray-800">${name}</td>
            <td class="px-5 py-4 text-sm text-gray-600">${Number(displayIncome).toLocaleString()}</td>
            <td class="px-5 py-4 text-sm text-center text-gray-600">${displayScore}</td>
            <td class="px-5 py-4 text-sm text-center">${statusHtml}</td>
            <td class="px-5 py-4 text-sm text-center">${contactStatusHtml}</td>
        `;
        tbody.appendChild(tr);
    }

    // Gắn event listener cho tất cả select
    document.querySelectorAll('.contact-status-select').forEach(select => {
        select.addEventListener('change', async (e) => {
            const status = e.target.value;
            const rowId = e.target.dataset.rowId;
            const rowNumber = e.target.dataset.rowNumber;
            const name = e.target.dataset.name;

            if (!status) {
                // Reset style khi chọn "--Chọn--"
                e.target.style.backgroundColor = 'white';
                e.target.style.color = '#333';
                return;
            }

            // Set màu dựa trên status
            if (status === 'da_lien_lac') {
                e.target.style.backgroundColor = '#dcfce7';
                e.target.style.color = '#166534';
                e.target.style.fontWeight = 'bold';
            } else if (status === 'chua_lien_lac') {
                e.target.style.backgroundColor = '#fef3c7';
                e.target.style.color = '#92400e';
                e.target.style.fontWeight = 'bold';
            } else if (status === 'khong_lien_lac_duoc') {
                e.target.style.backgroundColor = '#fee2e2';
                e.target.style.color = '#991b1b';
                e.target.style.fontWeight = 'bold';
            }

            console.log(`Row: ${rowNumber}, Name: ${name}, Status: ${status}`);
            
            // Visual feedback - highlight row
            const row = e.target.closest('tr');
            row.classList.add('bg-indigo-50');
            
            // Lưu vào localStorage để persist data
            const contactData = {
                rowNumber,
                name,
                status,
                timestamp: new Date().toISOString()
            };
            
            let allContacts = JSON.parse(localStorage.getItem('contactStatus') || '[]');
            const existingIndex = allContacts.findIndex(item => item.rowNumber == rowNumber);
            if (existingIndex !== -1) {
                allContacts[existingIndex] = contactData;
            } else {
                allContacts.push(contactData);
            }
            localStorage.setItem('contactStatus', JSON.stringify(allContacts));
        });
    });

    btnBatch.disabled = false;
    spinner.classList.add('hidden');
    
    // Enable Save button after batch processing
    document.getElementById('btnSave').disabled = false;
    document.getElementById('btnSave').classList.remove('bg-slate-300', 'cursor-not-allowed');
    document.getElementById('btnSave').classList.add('bg-emerald-600', 'hover:bg-emerald-700');
    
    // Setup sorting functionality
    setupTableSorting();
}

// =====================================================================
// 7. SORTING FUNCTIONALITY
// =====================================================================
let sortConfig = {
    column: null,
    direction: 'asc' // 'asc' or 'desc'
};

// Lưu trữ tên gốc của các cột
const columnNames = {
    'name': 'Họ tên',
    'income': 'Thu nhập',
    'score': 'Score',
    'result': 'Kết quả'
};

function setupTableSorting() {
    const headers = document.querySelectorAll('thead th[data-sort]');
    
    headers.forEach(header => {
        // Lưu tên gốc của cột vào data attribute
        const columnKey = header.dataset.sort;
        header.dataset.originalText = columnNames[columnKey];
        
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            const tbody = document.getElementById('resultTableBody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            // Nếu click vào cột khác, reset direction thành asc
            if (sortConfig.column !== column) {
                sortConfig.column = column;
                sortConfig.direction = 'asc';
            } else {
                // Nếu click vào cột cũ, toggle direction
                sortConfig.direction = sortConfig.direction === 'asc' ? 'desc' : 'asc';
            }

            // Sort rows
            rows.sort((rowA, rowB) => {
                let valueA, valueB;

                switch (column) {
                    case 'name':
                        valueA = rowA.cells[1].textContent.trim().toLowerCase();
                        valueB = rowB.cells[1].textContent.trim().toLowerCase();
                        return sortConfig.direction === 'asc' 
                            ? valueA.localeCompare(valueB, 'vi') 
                            : valueB.localeCompare(valueA, 'vi');

                    case 'income':
                        valueA = parseInt(rowA.cells[2].textContent.replace(/\D/g, '')) || 0;
                        valueB = parseInt(rowB.cells[2].textContent.replace(/\D/g, '')) || 0;
                        return sortConfig.direction === 'asc' 
                            ? valueA - valueB 
                            : valueB - valueA;

                    case 'score':
                        valueA = parseInt(rowA.cells[3].textContent) || 0;
                        valueB = parseInt(rowB.cells[3].textContent) || 0;
                        return sortConfig.direction === 'asc' 
                            ? valueA - valueB 
                            : valueB - valueA;

                    case 'result':
                        valueA = rowA.cells[4].textContent.toLowerCase().includes('thấp') ? 1 : 0;
                        valueB = rowB.cells[4].textContent.toLowerCase().includes('thấp') ? 1 : 0;
                        return sortConfig.direction === 'asc' 
                            ? valueA - valueB 
                            : valueB - valueA;

                    default:
                        return 0;
                }
            });

            // Clear tbody
            tbody.innerHTML = '';

            // Re-add sorted rows
            rows.forEach(row => tbody.appendChild(row));

            // Update header styles
            updateHeaderStyles(column);
        });
    });
}

function updateHeaderStyles(activeColumn) {
    const headers = document.querySelectorAll('thead th[data-sort]');
    headers.forEach(header => {
        const originalText = header.dataset.originalText;
        
        if (header.dataset.sort === activeColumn) {
            header.classList.add('bg-indigo-100');
            const arrow = sortConfig.direction === 'asc' ? '↑' : '↓';
            header.textContent = `${originalText} ${arrow}`;
        } else {
            header.classList.remove('bg-indigo-100');
            header.textContent = `${originalText} ↕`;
        }
    });
}

// =====================================================================
// 8. SAVE/LOAD RESULTS
// =====================================================================
function saveResults() {
    if (!isAuthenticated()) {
        alert('Vui lòng đăng nhập trước');
        return;
    }

    const tbody = document.getElementById('resultTableBody');
    const rows = tbody.querySelectorAll('tr');

    if (rows.length === 0) {
        alert('Không có dữ liệu để lưu');
        return;
    }

    // Collect data from current table
    const results = [];
    rows.forEach((row, index) => {
        const cells = row.cells;
        const selectElement = row.querySelector('.contact-status-select');
        
        results.push({
            rowNumber: index + 1,
            name: cells[1]?.textContent.trim() || '',
            income: cells[2]?.textContent.trim() || '',
            score: cells[3]?.textContent.trim() || '',
            result: cells[4]?.textContent.trim() || '',
            contactStatus: selectElement?.value || ''
        });
    });

    // Save to database via API
    fetch(`${API_BASE_URL}/save-results`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader()
        },
        body: JSON.stringify(results)
    })
    .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })
    .then(data => {
        if (data.success) {
            alert(`✓ Lưu thành công!\nThời gian: ${new Date(data.timestamp).toLocaleString('vi-VN')}\nSố bản ghi: ${results.length}\nSession ID: ${data.session_id}`);
            console.log('Saved to database:', data);
        } else {
            alert('Lỗi: ' + (data.message || 'Không thể lưu dữ liệu'));
        }
    })
    .catch(error => {
        console.error('Save error:', error);
        alert('Lỗi khi lưu dữ liệu: ' + error.message);
    });
}

function loadResults() {
    if (!isAuthenticated()) {
        alert('Vui lòng đăng nhập trước');
        return;
    }

    // Load all sessions from database
    fetch(`${API_BASE_URL}/load-results`, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader()
        }
    })
    .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })
    .then(data => {
        if (!data.success || data.sessions.length === 0) {
            alert(data.message || 'Không có dữ liệu đã lưu');
            return;
        }

        // Create a dialog to select which session to load
        const sessionList = data.sessions
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

        // Simple selection using prompt (can be improved with modal)
        let selectedIndex = 0;
        if (sessionList.length > 1) {
            const options = sessionList
                .map((s, i) => {
                    const date = new Date(s.timestamp).toLocaleString('vi-VN');
                    return `${i}: ${date} (${s.rowCount} bản ghi)`;
                })
                .join('\n');
            const input = prompt(`Chọn session để tải:\n${options}\n\nNhập số thứ tự (0-${sessionList.length - 1}):`, '0');
            
            if (input === null) return; // User cancelled
            
            selectedIndex = parseInt(input);
            if (isNaN(selectedIndex) || selectedIndex < 0 || selectedIndex >= sessionList.length) {
                alert('Lựa chọn không hợp lệ');
                return;
            }
        }

        const selectedSession = sessionList[selectedIndex];
        loadSessionData(selectedSession);
    })
    .catch(error => {
        console.error('Load error:', error);
        alert('Lỗi khi tải dữ liệu: ' + error.message);
    });
}

function loadSessionData(sessionData) {
    const tbody = document.getElementById('resultTableBody');
    tbody.innerHTML = '';

    sessionData.results.forEach((resultData, index) => {
        const tr = document.createElement('tr');
        tr.id = `row-${index + 1}`;
        tr.className = "hover:bg-slate-50 transition border-b border-gray-100";

        // Parse result status
        const isRiskLow = resultData.result.includes('thấp');
        const statusHtml = isRiskLow 
            ? `<span class="px-2 py-1 font-bold text-green-900 bg-green-200 rounded-full text-xs">Rủi ro thấp</span>`
            : `<span class="px-2 py-1 font-bold text-red-900 bg-red-200 rounded-full text-xs">Rủi ro cao</span>`;

        // Get contact status select HTML
        let selectBgColor = 'white';
        let selectTextColor = '#333';
        let selectText = resultData.contactStatus;

        if (resultData.contactStatus === 'da_lien_lac') {
            selectBgColor = '#dcfce7';
            selectTextColor = '#166534';
            selectText = '✓ Đã liên lạc';
        } else if (resultData.contactStatus === 'chua_lien_lac') {
            selectBgColor = '#fef3c7';
            selectTextColor = '#92400e';
            selectText = '○ Chưa liên lạc';
        } else if (resultData.contactStatus === 'khong_lien_lac_duoc') {
            selectBgColor = '#fee2e2';
            selectTextColor = '#991b1b';
            selectText = '✕ Không liên lạc được';
        }

        const contactStatusHtml = `
            <select class="contact-status-select px-2 py-1 border border-gray-300 rounded text-xs bg-white cursor-pointer hover:border-indigo-500 transition" 
                    data-row-id="row-${index + 1}" 
                    data-row-number="${resultData.rowNumber}" 
                    data-name="${resultData.name}"
                    style="background-color: ${selectBgColor}; color: ${selectTextColor}; font-weight: ${selectText ? 'bold' : 'normal'};">
                <option value="">-- Chọn --</option>
                <option value="da_lien_lac" style="background-color: #dcfce7; color: #166534;">✓ Đã liên lạc</option>
                <option value="chua_lien_lac" style="background-color: #fef3c7; color: #92400e;">○ Chưa liên lạc</option>
                <option value="khong_lien_lac_duoc" style="background-color: #fee2e2; color: #991b1b;">✕ Không liên lạc được</option>
            </select>
        `;

        tr.innerHTML = `
            <td class="px-5 py-4 text-sm text-gray-500 text-center">${resultData.rowNumber}</td>
            <td class="px-5 py-4 text-sm font-bold text-gray-800">${resultData.name}</td>
            <td class="px-5 py-4 text-sm text-gray-600">${resultData.income}</td>
            <td class="px-5 py-4 text-sm text-center text-gray-600">${resultData.score}</td>
            <td class="px-5 py-4 text-sm text-center">${statusHtml}</td>
            <td class="px-5 py-4 text-sm text-center">${contactStatusHtml}</td>
        `;

        tbody.appendChild(tr);

        // Set the select value after adding to DOM
        const select = tr.querySelector('.contact-status-select');
        if (select && resultData.contactStatus) {
            select.value = resultData.contactStatus;
        }
    });

    // Re-attach event listeners for contact status
    document.querySelectorAll('.contact-status-select').forEach(select => {
        select.addEventListener('change', async (e) => {
            const status = e.target.value;
            const rowNumber = e.target.dataset.rowNumber;
            const name = e.target.dataset.name;

            if (!status) {
                e.target.style.backgroundColor = 'white';
                e.target.style.color = '#333';
                return;
            }

            if (status === 'da_lien_lac') {
                e.target.style.backgroundColor = '#dcfce7';
                e.target.style.color = '#166534';
                e.target.style.fontWeight = 'bold';
            } else if (status === 'chua_lien_lac') {
                e.target.style.backgroundColor = '#fef3c7';
                e.target.style.color = '#92400e';
                e.target.style.fontWeight = 'bold';
            } else if (status === 'khong_lien_lac_duoc') {
                e.target.style.backgroundColor = '#fee2e2';
                e.target.style.color = '#991b1b';
                e.target.style.fontWeight = 'bold';
            }

            const row = e.target.closest('tr');
            row.classList.add('bg-indigo-50');

            // Save to localStorage
            const contactData = {
                rowNumber,
                name,
                status,
                timestamp: new Date().toISOString()
            };
            
            let allContacts = JSON.parse(localStorage.getItem('contactStatus') || '[]');
            const existingIndex = allContacts.findIndex(item => item.rowNumber == rowNumber);
            if (existingIndex !== -1) {
                allContacts[existingIndex] = contactData;
            } else {
                allContacts.push(contactData);
            }
            localStorage.setItem('contactStatus', JSON.stringify(allContacts));
        });
    });

    // Re-setup sorting
    setupTableSorting();

    // Enable Save button
    document.getElementById('btnSave').disabled = false;
    document.getElementById('btnSave').classList.remove('bg-slate-300', 'cursor-not-allowed');
    document.getElementById('btnSave').classList.add('bg-emerald-600', 'hover:bg-emerald-700');

    alert(`✓ Tải thành công!\nSố bản ghi: ${sessionData.rowCount}`);
}

// =====================================================================
// AUTO-CALCULATE LOAN PERCENT INCOME
// =====================================================================
function setupAutoCalculateLoanPercent() {
    const loanAmntInput = document.getElementById('loan_amnt');
    const personIncomeInput = document.getElementById('person_income');
    const loanPercentIncomeInput = document.getElementById('loan_percent_income');

    if (!loanAmntInput || !personIncomeInput || !loanPercentIncomeInput) return;

    function calculateLoanPercent() {
        const loanAmnt = parseFloat(loanAmntInput.value) || 0;
        const personIncome = parseFloat(personIncomeInput.value) || 0;

        if (personIncome > 0) {
            const loanPercent = loanAmnt / personIncome;
            loanPercentIncomeInput.value = loanPercent.toFixed(3);
        } else {
            loanPercentIncomeInput.value = '';
        }
    }

    loanAmntInput.addEventListener('input', calculateLoanPercent);
    personIncomeInput.addEventListener('input', calculateLoanPercent);
}

setupAutoCalculateLoanPercent();

// =====================================================================
// 9. EXCEL FILE READING FOR COMPARISON
// =====================================================================
function readExcelFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const data = new Uint8Array(e.target.result);
                const workbook = XLSX.read(data, { type: 'array' });
                const firstSheet = workbook.SheetNames[0];
                let jsonData = XLSX.utils.sheet_to_json(workbook.Sheets[firstSheet]);
                
                // Xử lý dữ liệu: Chuyển đổi cột text thành chữ thường và normalize
                jsonData = jsonData.map(row => {
                    const newRow = {};
                    for (const key in row) {
                        let value = row[key];
                        
                        // Chuyển text thành chữ thường để dễ so sánh
                        if (typeof value === 'string') {
                            value = value.toLowerCase().trim();
                        }
                        
                        newRow[key.toLowerCase().trim()] = value;
                    }
                    return newRow;
                });
                
                resolve(jsonData);
            } catch (err) {
                reject(err);
            }
        };
        reader.onerror = (err) => reject(err);
        reader.readAsArrayBuffer(file);
    });
}

// =====================================================================
// 10. MODEL COMPARISON FUNCTIONS
// =====================================================================
function updateModelMetrics(prefix, metrics) {
    if (!metrics || metrics.error) return;
    
    // Handle percentage or decimal
    const acc = metrics.accuracy > 1 ? metrics.accuracy : metrics.accuracy * 100;
    const time = Math.round(metrics.time);
    
    // Update main card display
    document.getElementById(`acc_${prefix}`).innerText = acc.toFixed(1) + '%';
    document.getElementById(`prec_${prefix}`).innerText = metrics.precision.toFixed(2);
    document.getElementById(`rec_${prefix}`).innerText = metrics.recall.toFixed(2);
    document.getElementById(`f1_${prefix}`).innerText = metrics.f1.toFixed(2);
    document.getElementById(`time_${prefix}`).innerText = time + ' ms';
    
    // Update bar charts for accuracy
    document.getElementById(`bar_acc_${prefix}`).innerText = acc.toFixed(1) + '%';
    const barElement = document.getElementById(`bar_${prefix}`);
    if (barElement) {
        barElement.style.width = acc + '%';
    }
    
    // Update table
    document.getElementById(`tbl_acc_${prefix}`).innerText = acc.toFixed(2) + '%';
    document.getElementById(`tbl_prec_${prefix}`).innerText = metrics.precision.toFixed(2);
    document.getElementById(`tbl_rec_${prefix}`).innerText = metrics.recall.toFixed(2);
    document.getElementById(`tbl_f1_${prefix}`).innerText = metrics.f1.toFixed(2);
    document.getElementById(`tbl_time_${prefix}`).innerText = time + ' ms';
}

function updateTimeComparison(results) {
    if (!results) return;
    
    // Find max time for scaling
    const times = [results.xgboost?.time || 0, results.random_forest?.time || 0, results.logistic_regression?.time || 0];
    const maxTime = Math.max(...times);
    
    if (maxTime > 0) {
        // XGBoost
        document.getElementById('time_bar_xgb').innerText = Math.round(results.xgboost.time) + ' ms';
        const xgbPercent = (results.xgboost.time / maxTime) * 100;
        document.getElementById('time_bar_xgb_fill').style.width = xgbPercent + '%';
        
        // Random Forest
        document.getElementById('time_bar_rf').innerText = Math.round(results.random_forest.time) + ' ms';
        const rfPercent = (results.random_forest.time / maxTime) * 100;
        document.getElementById('time_bar_rf_fill').style.width = rfPercent + '%';
        
        // Logistic Regression
        document.getElementById('time_bar_lr').innerText = Math.round(results.logistic_regression.time) + ' ms';
        const lrPercent = (results.logistic_regression.time / maxTime) * 100;
        document.getElementById('time_bar_lr_fill').style.width = lrPercent + '%';
    }
}

function updateBestBadge(results) {
    if (!results) return;
    
    // Hide all badges first
    document.getElementById('badge_xgb').classList.add('hidden');
    document.getElementById('badge_rf').classList.add('hidden');
    document.getElementById('badge_lr').classList.add('hidden');
    
    // Get accuracies
    const accuracies = {
        'xgb': results.xgboost?.accuracy || 0,
        'rf': results.random_forest?.accuracy || 0,
        'lr': results.logistic_regression?.accuracy || 0
    };
    
    // Find the model with highest accuracy
    let bestModel = 'xgb';
    let maxAccuracy = accuracies.xgb;
    
    if (accuracies.rf > maxAccuracy) {
        bestModel = 'rf';
        maxAccuracy = accuracies.rf;
    }
    if (accuracies.lr > maxAccuracy) {
        bestModel = 'lr';
        maxAccuracy = accuracies.lr;
    }
    
    // Show badge for best model
    document.getElementById(`badge_${bestModel}`).classList.remove('hidden');
}

async function runComparisonDemo() {
    const fileInput = document.getElementById('testDatasetFile');
    if (!fileInput.files || fileInput.files.length === 0) {
        alert("Vui lòng chọn file dữ liệu kiểm thử (Excel/CSV) trước khi chạy đánh giá!");
        return;
    }

    if (typeof isAuthenticated === 'function' && !isAuthenticated()) {
        alert("Vui lòng đăng nhập để thực hiện chức năng này!");
        return;
    }

    const btn = document.getElementById('btnRunComparison');
    const originalText = btn.innerHTML;
    btn.innerHTML = `<div class="loader ease-linear rounded-full border-2 border-t-2 border-white h-5 w-5"></div><span>ĐANG CHẠY...</span>`;
    btn.disabled = true;

    try {
        const file = fileInput.files[0];
        let jsonData = await readExcelFile(file);

        if (jsonData.length === 0) {
            throw new Error("File không có dữ liệu!");
        }

        // Log để debug
        console.log("Excel data loaded:", jsonData.slice(0, 2));

        // Call API endpoint /evaluate
        // Note: API_BASE_URL is defined in script.js
        const response = await fetch(`${API_BASE_URL}/evaluate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(typeof getAuthHeader === 'function' ? getAuthHeader() : {})
            },
            body: JSON.stringify(jsonData)
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            console.error("API Response Error:", errData);
            throw new Error(errData.detail || `Lỗi server: ${response.status}`);
        }

        const results = await response.json();
        
        console.log("Comparison results:", results);
        
        // Update UI with real data
        updateModelMetrics('xgb', results.xgboost);
        updateModelMetrics('rf', results.random_forest);
        updateModelMetrics('lr', results.logistic_regression);
        updateTimeComparison(results);
        updateBestBadge(results);
        
        alert("✓ Chạy so sánh thành công!");

    } catch (error) {
        console.error("Comparison Error:", error);
        alert("Có lỗi xảy ra: " + error.message);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initAuthUI);

