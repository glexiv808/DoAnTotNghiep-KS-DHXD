// =====================================================================
// 1. CẤU HÌNH HỆ THỐNG
// =====================================================================
const API_URL = 'http://34.87.54.108.nip.io/predict';

// CHÚ Ý: CẬP NHẬT THÔNG SỐ NÀY TỪ PYTHON NOTEBOOK CỦA BẠN
const SCALER_CONFIG = {
    person_age: { mean: 27.73, scale: 6.34 },
    person_income: { mean: 66079, scale: 61983 },
    person_emp_exp: { mean: 4.78, scale: 4.14 },
    loan_amnt: { mean: 9589, scale: 6322 },
    loan_int_rate: { mean: 11.01, scale: 3.24 },
    loan_percent_income: { mean: 0.17, scale: 0.10 },
    cb_person_cred_hist_length: { mean: 5.80, scale: 4.05 },
    credit_score: { mean: 650, scale: 50 },
};

// Từ điển Mapping (Chữ -> Số)
const CAT_MAP = {
    person_gender: { 'female': 0, 'male': 1, 'nu': 0, 'nam': 1 },
    person_education: { 'high school': 0, 'associate': 1, 'bachelor': 2, 'master': 3, 'doctorate': 4 },
    person_home_ownership: { 'rent': 0, 'mortgage': 1, 'own': 2, 'other': 3 },
    loan_intent: { 'education': 0, 'medical': 1, 'venture': 2, 'personal': 3, 'debtconsolidation': 4, 'homeimprovement': 5 },
    previous_loan_defaults_on_file: { 'no': 0, 'yes': 1, 'khong': 0, 'co': 1 }
};

// Thứ tự này PHẢI KHỚP với thứ tự lúc train model
const FIELD_LIST = [
    'person_age', 'person_gender', 'person_education', 'person_income',
    'person_emp_exp', 'person_home_ownership', 'loan_amnt', 'loan_intent',
    'loan_int_rate', 'loan_percent_income', 'cb_person_cred_hist_length',
    'credit_score', 'previous_loan_defaults_on_file'
];

// =====================================================================
// 2. LOGIC XỬ LÝ DỮ LIỆU (Mapping + Scaling)
// =====================================================================
function preprocessValue(key, value) {
    // 1. Mapping
    if (CAT_MAP[key]) {
        const normalizedVal = String(value).toLowerCase().trim();
        if (CAT_MAP[key][normalizedVal] !== undefined) {
            value = CAT_MAP[key][normalizedVal];
        }
    }

    // 2. Ép kiểu số
    let numVal = Number(value);
    if (isNaN(numVal)) numVal = 0;

    // 3. Standard Scaling
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
// 3. XỬ LÝ FORM NHẬP LẺ
// =====================================================================
const singleForm = document.getElementById('singleForm');
if (singleForm) {
    singleForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        const btn = document.getElementById('btnSingle');
        const spinner = document.getElementById('spinnerSingle');
        const resBox = document.getElementById('resultSingle');

        // UI Loading
        btn.disabled = true;
        spinner.classList.remove('hidden');
        resBox.classList.add('hidden');

        // B1: Xử lý dữ liệu vào object tạm
        const processedData = {};
        FIELD_LIST.forEach(field => {
            const rawVal = document.getElementById(field).value;
            processedData[field] = preprocessValue(field, rawVal);
        });

        // B2: Chuyển thành Vector (Mảng số) theo đúng thứ tự
        const vectorPayload = FIELD_LIST.map(field => processedData[field]);

        // B3: Đóng gói để gửi đi (API cần list of lists: [[...]])
        const bodyToSend = vectorPayload;

        console.log("Vector gửi đi:", bodyToSend);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyToSend)
            });

            if (!response.ok) throw new Error("Lỗi kết nối Server API");

            const data = await response.json();
            console.log("Server trả về:", data); // Debug xem log

            // API trả về: { "prediction": [1], "status": "success" }
            let resultValue = 0; // Mặc định là 0 (Từ chối)

            if (data.prediction && Array.isArray(data.prediction)) {
                resultValue = data.prediction[0]; // Lấy số 1 trong mảng [1]
            } else if (data.loan_status !== undefined) {
                resultValue = data.loan_status; // Fallback cho trường hợp cũ
            }
            // --------------------

            // Hiển thị kết quả
            resBox.classList.remove('hidden');

            // So sánh resultValue thay vì status
            if (resultValue == 1) {
                resBox.className = "mt-4 p-4 rounded-lg border-2 text-center bg-green-50 border-green-500 text-green-800";
                document.getElementById('resTitleSingle').innerText = "DUYỆT VAY";
                document.getElementById('resMsgSingle').innerText = "Hồ sơ đủ điều kiện (Prediction: 1)";
            } else {
                resBox.className = "mt-4 p-4 rounded-lg border-2 text-center bg-red-50 border-red-500 text-red-800";
                document.getElementById('resTitleSingle').innerText = "TỪ CHỐI";
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
// 4. XỬ LÝ UPLOAD EXCEL / CSV
// =====================================================================
let batchData = [];
const fileInput = document.getElementById('excelFile');
const btnBatch = document.getElementById('btnBatch');
const fileInfo = document.getElementById('fileInfo');

// =====================================================================
// 5. LOGIC KIỂM TRA TÍNH HỢP LỆ CỦA FORM (UX)
// =====================================================================

function setupSingleFormValidation() {
    // Sử dụng FIELD_LIST đã được định nghĩa ở trên (13 trường)
    const fields = FIELD_LIST;
    const form = document.getElementById('singleForm');
    const submitButton = document.getElementById('btnSingle');

    if (!form || !submitButton) return;

    // Hàm kiểm tra tất cả các trường
    function checkFormValidity() {
        let allValid = true;

        for (const fieldId of fields) {
            const inputElement = document.getElementById(fieldId);

            // Kiểm tra: Phải tồn tại và không được rỗng/chỉ chứa khoảng trắng
            if (!inputElement || String(inputElement.value).trim() === '') {
                allValid = false;
                break;
            }
        }

        // Cập nhật trạng thái nút
        submitButton.disabled = !allValid;

        // Cập nhật màu nút
        if (allValid) {
            submitButton.classList.replace('bg-slate-300', 'bg-indigo-600');
            submitButton.classList.add('hover:bg-indigo-700');
        } else {
            submitButton.classList.replace('bg-indigo-600', 'bg-slate-300');
            submitButton.classList.remove('hover:bg-indigo-700');
        }
    }

    // Gắn sự kiện kiểm tra cho form khi người dùng nhập hoặc chọn
    form.addEventListener('input', checkFormValidity);
    form.addEventListener('change', checkFormValidity); // Quan trọng cho các thẻ <select>

    // Chạy kiểm tra ban đầu (để khóa nút nếu các trường là trống)
    checkFormValidity();
}

// Gọi hàm này để khởi động logic kiểm tra
setupSingleFormValidation();

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

// Hàm xử lý hàng loạt
async function processBatch() {
    if (batchData.length === 0) return alert("File không có dữ liệu!");

    const spinner = document.getElementById('spinnerBatch');
    const tbody = document.getElementById('resultTableBody');

    btnBatch.disabled = true;
    spinner.classList.remove('hidden');
    tbody.innerHTML = "";

    let count = 0;
    for (const row of batchData) {
        count++;
        console.log(`--- Row ${count} RAW Data ---`);
        console.log(row);
        const name = row['Ho_ten'] || row['Name'] || row['HO_TEN'] || row['Full Name'] || `Hồ sơ #${count}`;

        // B1: Xử lý dữ liệu từng dòng
        const processedData = {};
        FIELD_LIST.forEach(key => {
            const rowKey = Object.keys(row).find(k => k.toLowerCase() === key.toLowerCase());
            const rawVal = rowKey ? row[rowKey] : 0;
            processedData[key] = preprocessValue(key, rawVal);
        });

        // B2: Chuyển thành Vector
        const vectorPayload = FIELD_LIST.map(key => processedData[key]);

        // B3: Đóng gói [[...]]
        const bodyToSend = vectorPayload;

        let statusHtml = `<span class="text-gray-400 text-xs italic">Đang xử lý...</span>`;
        let displayStatus = -1;

        try {
            const res = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyToSend)
            });
            if (res.ok) {
                const data = await res.json();

                if (data.prediction && Array.isArray(data.prediction)) {
                    displayStatus = data.prediction[0];
                } else if (data.loan_status !== undefined) {
                    displayStatus = data.loan_status;
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

        // Lấy giá trị thô để hiển thị lên bảng thay vì giá trị đã scale
        const displayIncome = row['person_income'] || row['Person_Income'] || 0;
        const displayScore = row['credit_score'] || row['Credit_Score'] || '-';

        const tr = document.createElement('tr');
        tr.className = "hover:bg-slate-50 transition border-b border-gray-100";
        tr.innerHTML = `
            <td class="px-5 py-4 text-sm text-gray-500 text-center">${count}</td>
            <td class="px-5 py-4 text-sm font-bold text-gray-800">${name}</td>
            <td class="px-5 py-4 text-sm text-gray-600">${Number(displayIncome).toLocaleString()}</td>
            <td class="px-5 py-4 text-sm text-center text-gray-600">${displayScore}</td>
            <td class="px-5 py-4 text-sm text-center">${statusHtml}</td>
        `;
        tbody.appendChild(tr);
    }

    btnBatch.disabled = false;
    spinner.classList.add('hidden');
    // alert("Đã xử lý xong toàn bộ danh sách!");
}

