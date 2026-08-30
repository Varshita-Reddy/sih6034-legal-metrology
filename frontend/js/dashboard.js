const API_BASE_URL = 'http://127.0.0.1:8000';

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput') || document.getElementById('imageInput') || document.querySelector('input[type="file"]');
    const scanBtn = document.getElementById('scanBtn') || document.getElementById('analyzeBtn') || document.querySelector('.scan-btn');
    const dropZone = document.getElementById('dropZone') || document.querySelector('.drop-zone') || document.querySelector('.upload-area');
    const previewImage = document.getElementById('previewImage') || document.getElementById('imagePreview');
    const resultsSection = document.getElementById('resultsSection') || document.getElementById('results') || document.querySelector('.results-container');
    const loadingSpinner = document.getElementById('loadingSpinner') || document.getElementById('loader') || document.querySelector('.spinner');

    let selectedFile = null;

    // Handle File Selection
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                selectedFile = e.target.files[0];
                showPreview(selectedFile);
            }
        });
    }

    // Handle Drag and Drop
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                selectedFile = e.dataTransfer.files[0];
                showPreview(selectedFile);
            }
        });

        dropZone.addEventListener('click', () => {
            if (fileInput) fileInput.click();
        });
    }

    function showPreview(file) {
        if (previewImage) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImage.src = e.target.result;
                previewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
        if (typeof showToast === 'function') {
            showToast('Image selected: ' + file.name);
        }
    }

    // Handle Scan Button Click
    if (scanBtn) {
        scanBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!selectedFile && fileInput && fileInput.files[0]) {
                selectedFile = fileInput.files[0];
            }

            if (!selectedFile) {
                alert('Please upload or select a product label image first.');
                return;
            }

            await executeScan(selectedFile);
        });
    }

    async function executeScan(file) {
        // UI Loading State
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (scanBtn) {
            scanBtn.disabled = true;
            scanBtn.textContent = 'Scanning & Verifying (OCR)...';
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            console.log('Sending request to', `${API_BASE_URL}/scan`);
            const response = await fetch(`${API_BASE_URL}/scan`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `Server responded with status ${response.status}`);
            }

            const data = await response.json();
            console.log('Scan Successful:', data);

            // Save to inspection history
            if (typeof saveInspection === 'function') {
                saveInspection({
                    id: Date.now(),
                    date: new Date().toISOString(),
                    filename: data.filename || file.name,
                    compliant: data.compliant,
                    overall_status: data.overall_status,
                    extracted_fields: data.extracted_fields || data.fields,
                    report_url: data.report_url
                });
            }

            // Render Results on UI
            renderDashboardResults(data);

            if (typeof showToast === 'function') {
                showToast('Scan Completed: ' + data.overall_status);
            }

        } catch (error) {
            console.error('Scan Failed:', error);
            alert('Scan Failed: ' + error.message);
        } finally {
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (scanBtn) {
                scanBtn.disabled = false;
                scanBtn.textContent = 'Scan Label';
            }
        }
    }

    function renderDashboardResults(data) {
        if (resultsSection) {
            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }

        // 1. Status Badge
        const statusBadge = document.getElementById('complianceStatus') || document.getElementById('overallStatus') || document.querySelector('.status-badge');
        if (statusBadge) {
            const isCompliant = data.compliant;
            statusBadge.textContent = isCompliant ? '🟢 COMPLIANT' : '🔴 NON-COMPLIANT';
            statusBadge.className = isCompliant ? 'status-badge compliant' : 'status-badge non-compliant';
        }

        // 2. Extracted Fields
        const fields = data.extracted_fields || data.fields || {};
        
        const setFieldText = (elementId, value) => {
            const el = document.getElementById(elementId);
            if (el) el.textContent = value || 'Not Detected';
        };

        const getVal = (fieldObj) => {
            if (!fieldObj) return null;
            if (typeof fieldObj === 'string') return fieldObj;
            return fieldObj.value || null;
        };

        setFieldText('mrpValue', getVal(fields.mrp));
        setFieldText('netQtyValue', getVal(fields.net_quantity));
        setFieldText('mfgDateValue', getVal(fields.manufacturing_date));
        setFieldText('bestBeforeValue', getVal(fields.best_before));
        setFieldText('mfrValue', getVal(fields.manufacturer));

        // 3. Action Guidance
        const actionMessage = document.getElementById('actionMessage') || document.getElementById('frontendInstruction');
        if (actionMessage && data.frontend_action) {
            actionMessage.textContent = data.frontend_action.user_message || data.frontend_action.reason || '';
        }

        // 4. Report Download Button
        const reportBtn = document.getElementById('downloadReportBtn') || document.getElementById('reportLink') || document.querySelector('.download-report-btn');
        if (reportBtn) {
            if (data.report_url) {
                reportBtn.href = data.report_url;
                reportBtn.target = '_blank';
                reportBtn.style.display = 'inline-block';
            } else {
                reportBtn.style.display = 'none';
            }
        }
    }
});