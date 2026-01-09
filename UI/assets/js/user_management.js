// =====================================================================
// USER MANAGEMENT SCRIPT
// =====================================================================
const API_BASE_URL = 'http://34.87.54.108.nip.io';
// const API_BASE_URL = 'http://127.0.0.1:8000';
let currentPage = 1;
let currentSearch = '';
let currentUserId = null;
let isEditMode = false;

// Get token from localStorage
function getToken() {
    return localStorage.getItem('access_token');
}

function getAuthHeader() {
    const token = getToken();
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// Check if user is authenticated and is admin
async function checkAdminAccess() {
    const token = getToken();
    if (!token) {
        window.location.href = 'index.html';
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/users/me`, {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        if (!response.ok) {
            window.location.href = 'index.html';
            return false;
        }
        
        const user = await response.json();
        if (user.role !== 'admin') {
            alert('Bạn không có quyền truy cập trang này');
            window.location.href = 'index.html';
            return false;
        }
        
        // Display user info
        document.getElementById('currentUser').textContent = user.username;
        document.getElementById('userRole').textContent = `Role: ${user.role === 'admin' ? 'Quản trị viên' : 'Người dùng'}`;
        
        return true;
    } catch (error) {
        console.error('Error checking access:', error);
        window.location.href = 'index.html';
        return false;
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/stats`, {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        if (!response.ok) throw new Error('Failed to load stats');
        
        const stats = await response.json();
        document.getElementById('stat-total-users').textContent = stats.total_users;
        document.getElementById('stat-active-users').textContent = stats.active_users;
        document.getElementById('stat-admin-users').textContent = stats.admin_users;
        document.getElementById('stat-regular-users').textContent = stats.regular_users;
        document.getElementById('stat-total-contracts').textContent = stats.total_contracts;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load users list
async function loadUsers(page = 1, search = '') {
    try {
        const url = new URL(`${API_BASE_URL}/admin/users`);
        url.searchParams.append('page', page);
        url.searchParams.append('per_page', 10);
        if (search) url.searchParams.append('search', search);
        
        const response = await fetch(url.toString(), {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        // Handle response regardless of status
        const data = await response.json();
        
        if (!response.ok) {
            console.error('Failed to load users:', data);
            return;
        }
        
        displayUsersTable(data.users);
        displayPagination(data.page, data.pages, data.total, data.per_page);
        
        document.getElementById('userCountBadge').textContent = data.total;
        document.getElementById('totalUsers').textContent = data.total;
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Display users in table
function displayUsersTable(users) {
    const tbody = document.getElementById('usersTableBody');
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="px-6 py-8 text-center text-gray-500">Không có người dùng nào</td></tr>';
        return;
    }
    
    tbody.innerHTML = users.map(user => `
        <tr class="border-b border-slate-200 hover:bg-slate-50 transition">
            <td class="px-6 py-4 font-semibold text-indigo-900">${user.username}</td>
            <td class="px-6 py-4 text-gray-700">${user.email}</td>
            <td class="px-6 py-4 text-gray-700">${user.full_name || '-'}</td>
            <td class="px-6 py-4 text-center">
                <span class="px-3 py-1 rounded-full text-xs font-bold text-white ${user.role === 'admin' ? 'bg-amber-600' : 'bg-blue-600'}">
                    ${user.role === 'admin' ? 'Admin' : 'User'}
                </span>
            </td>
            <td class="px-6 py-4 text-center">
                <span class="px-3 py-1 rounded-full text-xs font-bold text-white ${user.is_active ? 'bg-green-600' : 'bg-red-600'}">
                    ${user.is_active ? 'Hoạt động' : 'Vô hiệu'}
                </span>
            </td>
            <td class="px-6 py-4 text-center font-semibold text-indigo-600">${user.contracts_count}</td>
            <td class="px-6 py-4 text-center text-gray-600">${new Date(user.created_at).toLocaleDateString('vi-VN')}</td>
            <td class="px-6 py-4 text-center">
                <button onclick="viewUserDetail(${user.id})" class="text-blue-600 hover:text-blue-800 font-medium mr-2">Chi tiết</button>
                <button onclick="editUser(${user.id})" class="text-indigo-600 hover:text-indigo-800 font-medium mr-2">Sửa</button>
                <button onclick="deleteUser(${user.id}, '${user.username}')" class="text-red-600 hover:text-red-800 font-medium">Xóa</button>
            </td>
        </tr>
    `).join('');
}

// Display pagination
function displayPagination(currentPage, totalPages, total, perPage) {
    const container = document.getElementById('paginationControls');
    let html = '';
    
    // Previous button
    if (currentPage > 1) {
        html += `<button onclick="loadUsers(${currentPage - 1}, '${currentSearch}')" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">← Trước</button>`;
    }
    
    // Page numbers
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        if (i === currentPage) {
            html += `<button class="px-3 py-2 bg-indigo-600 text-white rounded-lg">${i}</button>`;
        } else {
            html += `<button onclick="loadUsers(${i}, '${currentSearch}')" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">${i}</button>`;
        }
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `<button onclick="loadUsers(${currentPage + 1}, '${currentSearch}')" class="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition">Tiếp →</button>`;
    }
    
    container.innerHTML = html;
    
    // Update showing info
    const from = (currentPage - 1) * perPage + 1;
    const to = Math.min(currentPage * perPage, total);
    document.getElementById('showingFrom').textContent = from;
    document.getElementById('showingTo').textContent = to;
}

// View user detail
async function viewUserDetail(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        if (!response.ok) {
            console.error('Failed to load user detail');
            alert('Lỗi khi tải thông tin người dùng');
            return;
        }
        
        const user = await response.json();
        currentUserId = userId;
        
        // Populate modal
        document.getElementById('modal-username').textContent = user.username;
        document.getElementById('modal-email').textContent = user.email;
        document.getElementById('modal-fullname').textContent = user.full_name || '-';
        document.getElementById('modal-role').textContent = user.role === 'admin' ? 'Quản trị viên' : 'Người dùng';
        document.getElementById('modal-role').className = `inline-block px-3 py-1 rounded-full text-xs font-bold text-white ${user.role === 'admin' ? 'bg-amber-600' : 'bg-blue-600'}`;
        document.getElementById('modal-status').textContent = user.is_active ? 'Hoạt động' : 'Vô hiệu hóa';
        document.getElementById('modal-status').className = `inline-block px-3 py-1 rounded-full text-xs font-bold text-white ${user.is_active ? 'bg-green-600' : 'bg-red-600'}`;
        document.getElementById('modal-created').textContent = new Date(user.created_at).toLocaleDateString('vi-VN');
        document.getElementById('modal-last-login').textContent = user.last_login ? new Date(user.last_login).toLocaleDateString('vi-VN') : 'Chưa đăng nhập';
        document.getElementById('modal-contracts-count').textContent = user.contracts_count;
        
        // Display contracts
        displayContracts(user.contracts || []);
        
        // Show modal
        document.getElementById('userDetailModal').classList.remove('hidden');
        
        // Setup button listeners for this modal
        setupModalButtonListeners();
    } catch (error) {
        console.error('Error loading user detail:', error);
        alert('Lỗi khi tải thông tin người dùng');
    }
}

// Display contracts
function displayContracts(contracts) {
    const container = document.getElementById('contractsList');
    
    if (!contracts || contracts.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-center py-8">Người dùng này không có hợp đồng nào</p>';
        return;
    }
    
    container.innerHTML = contracts.map(contract => `
        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition">
            <div class="flex justify-between items-start mb-2">
                <div>
                    <p class="font-bold text-gray-900">Số HĐ: ${contract.contractNumber}</p>
                    <p class="text-sm text-gray-600">Khách hàng: ${contract.customerName}</p>
                </div>
                <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs font-bold rounded">${contract.status}</span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-sm text-gray-700">
                <div>Số tiền: <span class="font-semibold">${contract.loanAmount}</span></div>
                <div>Lãi suất: <span class="font-semibold">${contract.interestRate}%</span></div>
                <div>Kỳ hạn: <span class="font-semibold">${contract.loanDuration} tháng</span></div>
                <div>Ngày tạo: <span class="font-semibold">${new Date(contract.created_at).toLocaleDateString('vi-VN')}</span></div>
            </div>
        </div>
    `).join('');
}

// Edit user
async function editUser(userId) {
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        if (!response.ok) {
            console.error('Failed to load user');
            alert('Lỗi khi tải thông tin người dùng');
            return;
        }
        
        const user = await response.json();
        currentUserId = userId;
        isEditMode = true;
        
        // Populate form
        document.getElementById('form-username').value = user.username;
        document.getElementById('form-username').disabled = true;
        document.getElementById('form-email').value = user.email;
        document.getElementById('form-fullname').value = user.full_name || '';
        document.getElementById('form-role').value = user.role;
        document.getElementById('form-active').value = user.is_active;
        
        // Hide password field for edit
        document.getElementById('passwordDiv').style.display = 'none';
        document.getElementById('modal-title').textContent = 'Chỉnh sửa Người dùng';
        document.getElementById('form-submit-text').textContent = 'Cập nhật';
        
        document.getElementById('userDetailModal').classList.add('hidden');
        document.getElementById('addEditUserModal').classList.remove('hidden');
    } catch (error) {
        console.error('Error loading user:', error);
        alert('Lỗi khi tải thông tin người dùng');
    }
}

// Delete user
async function deleteUser(userId, username) {
    if (!confirm(`Bạn chắc chắn muốn xóa người dùng "${username}"? Tất cả hợp đồng của họ cũng sẽ bị xóa.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
        
        if (!response.ok) throw new Error('Failed to delete user');
        
        alert('Xóa người dùng thành công');
        closeUserDetailModal();
        loadUsers(currentPage, currentSearch);
        loadStats();
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Lỗi khi xóa người dùng');
    }
}

// Close user detail modal
function closeUserDetailModal() {
    document.getElementById('userDetailModal').classList.add('hidden');
}

// Open add user modal
function openAddUserModal() {
    currentUserId = null;
    isEditMode = false;
    
    // Reset form
    document.getElementById('addEditUserForm').reset();
    document.getElementById('form-username').disabled = false;
    document.getElementById('passwordDiv').style.display = 'block';
    document.getElementById('modal-title').textContent = 'Thêm Người dùng';
    document.getElementById('form-submit-text').textContent = 'Thêm';
    document.getElementById('form-error').classList.add('hidden');
    
    document.getElementById('addEditUserModal').classList.remove('hidden');
}

// Close add/edit modal
function closeAddEditModal() {
    document.getElementById('addEditUserModal').classList.add('hidden');
}

// Submit form
document.getElementById('addEditUserForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('form-username').value.trim();
    const email = document.getElementById('form-email').value.trim();
    const password = document.getElementById('form-password').value;
    const fullname = document.getElementById('form-fullname').value.trim();
    const role = document.getElementById('form-role').value;
    const active = document.getElementById('form-active').value === 'true';
    
    const errorDiv = document.getElementById('form-error');
    errorDiv.classList.add('hidden');
    
    // Validation
    if (!username || !email) {
        errorDiv.textContent = 'Vui lòng điền tất cả các trường bắt buộc';
        errorDiv.classList.remove('hidden');
        return;
    }
    
    if (!isEditMode && !password) {
        errorDiv.textContent = 'Vui lòng nhập mật khẩu';
        errorDiv.classList.remove('hidden');
        return;
    }
    
    if (!isEditMode && password.length < 6) {
        errorDiv.textContent = 'Mật khẩu phải có ít nhất 6 ký tự';
        errorDiv.classList.remove('hidden');
        return;
    }
    
    try {
        if (isEditMode) {
            // Update user
            const response = await fetch(`${API_BASE_URL}/admin/users/${currentUserId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                },
                body: JSON.stringify({
                    email,
                    full_name: fullname,
                    role,
                    is_active: active
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to update user');
            }
            
            alert('Cập nhật người dùng thành công');
        } else {
            // Create new user
            const response = await fetch(`${API_BASE_URL}/admin/users?role=${role}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeader()
                },
                body: JSON.stringify({
                    username,
                    email,
                    password,
                    full_name: fullname
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to create user');
            }
            
            alert('Tạo người dùng thành công');
        }
        
        closeAddEditModal();
        loadUsers(currentPage, currentSearch);
        loadStats();
    } catch (error) {
        console.error('Error:', error);
        errorDiv.textContent = error.message;
        errorDiv.classList.remove('hidden');
    }
});

// Search functionality
document.getElementById('searchInput')?.addEventListener('input', (e) => {
    currentSearch = e.target.value;
    loadUsers(1, currentSearch);
});

// Add user button
document.getElementById('btnAddUser')?.addEventListener('click', openAddUserModal);

// Logout button
document.getElementById('btnLogout')?.addEventListener('click', async (e) => {
    e.preventDefault();
    
    try {
        await fetch(`${API_BASE_URL}/logout`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeader()
            }
        });
    } catch (error) {
        console.error('Logout error:', error);
    }
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_role');
    window.location.href = 'index.html';
});

// Setup modal buttons event listeners
function setupModalButtonListeners() {
    const editBtn = document.getElementById('modal-btn-edit');
    const deleteBtn = document.getElementById('modal-btn-delete');
    
    // Remove old listeners by cloning
    if (editBtn) {
        const newEditBtn = editBtn.cloneNode(true);
        editBtn.parentNode.replaceChild(newEditBtn, editBtn);
        
        newEditBtn.addEventListener('click', () => {
            if (currentUserId) {
                editUser(currentUserId);
            }
        });
    }
    
    if (deleteBtn) {
        const newDeleteBtn = deleteBtn.cloneNode(true);
        deleteBtn.parentNode.replaceChild(newDeleteBtn, deleteBtn);
        
        newDeleteBtn.addEventListener('click', () => {
            if (currentUserId) {
                // Get username from modal for confirmation
                const username = document.getElementById('modal-username').textContent;
                deleteUser(currentUserId, username);
            }
        });
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    const hasAccess = await checkAdminAccess();
    if (hasAccess) {
        loadStats();
        loadUsers();
        setupModalButtonListeners();
    }
});
