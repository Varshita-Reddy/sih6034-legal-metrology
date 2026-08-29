document.addEventListener('DOMContentLoaded', function () {
    const officerName = document.getElementById('officerName');
    const welcomeName = document.getElementById('welcomeName');
    const officerAvatar = document.getElementById('officerAvatar');

    if (officerName) {
        const stored = localStorage.getItem('legalMetrixOfficerName');
        const displayName = stored && stored.trim() ? stored.trim() : 'User';
        officerName.textContent = displayName;
        if (welcomeName) welcomeName.textContent = displayName;
        if (officerAvatar) officerAvatar.textContent = displayName.charAt(0).toUpperCase();
    }

    loadDashboardStats();
    restoreRetakeInspection();

    const input = document.getElementById('productImage');
    const uploadArea = document.getElementById('uploadArea');
    const analyzeButton = document.getElementById('analyzeButton');
    const removeButton = document.getElementById('removeImage');
    const newScanButton = document.getElementById('newScanButton');
    const saveResultButton = document.getElementById('saveResultButton');
    const cameraButton = document.getElementById('cameraButton');
    const captureButton = document.getElementById('captureButton');
    const closeCameraButton = document.getElementById('closeCameraButton');

    if (input) {
        input.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                handleImage(this.files[0]);
            }
        });
    }

    if (uploadArea) {
        uploadArea.addEventListener('dragover', function (event) {
            event.preventDefault();
            uploadArea.classList.add('dragging');
        });

        uploadArea.addEventListener('dragleave', function () {
            uploadArea.classList.remove('dragging');
        });

        uploadArea.addEventListener('drop', function (event) {
            event.preventDefault();
            uploadArea.classList.remove('dragging');
            const file = event.dataTransfer.files[0];
            if (file) handleImage(file);
        });
    }

    if (removeButton) removeButton.addEventListener('click', removeImage);
    if (analyzeButton) analyzeButton.addEventListener('click', analyzeProduct);
    if (newScanButton) newScanButton.addEventListener('click', resetScanner);
    if (saveResultButton) saveResultButton.addEventListener('click', saveCurrentInspection);
    if (cameraButton) cameraButton.addEventListener('click', openCamera);
    if (captureButton) captureButton.addEventListener('click', captureImage);
    if (closeCameraButton) closeCameraButton.addEventListener('click', closeCamera);
});

let cameraStream = null;

async function openCamera() {
    const cameraPanel = document.getElementById('cameraPanel');
    const cameraPreview = document.getElementById('cameraPreview');
    const cameraMessage = document.getElementById('cameraMessage');
    const captureButton = document.getElementById('captureButton');

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('Camera access is not supported by this browser.');
        return;
    }

    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: 'environment' } },
            audio: false
        });

        cameraPreview.srcObject = cameraStream;
        cameraPanel.classList.remove('hidden');
        cameraPanel.setAttribute('aria-hidden', 'false');
        cameraMessage.textContent = 'Position the product label inside the frame.';
        captureButton.disabled = false;
    } catch (error) {
        cameraMessage.textContent = 'Camera access was blocked. Check browser permissions and try again.';
        showToast('Unable to access the camera.');
    }
}

function captureImage() {
    const cameraPreview = document.getElementById('cameraPreview');

    if (!cameraStream || !cameraPreview.videoWidth) {
        showToast('Camera is not ready yet.');
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = cameraPreview.videoWidth;
    canvas.height = cameraPreview.videoHeight;
    canvas.getContext('2d').drawImage(cameraPreview, 0, 0);

    canvas.toBlob(function (blob) {
        if (blob) {
            handleImage(new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' }));
            closeCamera();
        } else {
            showToast('Unable to capture an image.');
        }
    }, 'image/jpeg', 0.92);
}

function closeCamera() {
    const cameraPanel = document.getElementById('cameraPanel');
    const cameraPreview = document.getElementById('cameraPreview');

    if (cameraStream) {
        cameraStream.getTracks().forEach(function (track) {
            track.stop();
        });
        cameraStream = null;
    }

    cameraPreview.srcObject = null;
    cameraPanel.classList.add('hidden');
    cameraPanel.setAttribute('aria-hidden', 'true');
}

function handleImage(file) {
    if (!file.type.startsWith('image/')) {
        showToast('Please select an image file.');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        showToast('Image must be smaller than 10 MB.');
        return;
    }

    selectedImage = file;

    const reader = new FileReader();
    reader.onload = function (event) {
        const preview = document.getElementById('previewImage');
        const previewContainer = document.getElementById('previewContainer');
        const selectedFileName = document.getElementById('selectedFileName');
        const analyzeButton = document.getElementById('analyzeButton');

        if (preview) {
            preview.src = event.target.result;
            preview.dataset.image = event.target.result;
        }

        if (previewContainer) previewContainer.classList.remove('hidden');
        if (selectedFileName) selectedFileName.textContent = file.name;
        if (analyzeButton) analyzeButton.disabled = false;
    };

    reader.readAsDataURL(file);
}

function removeImage() {
    selectedImage = null;

    const productImage = document.getElementById('productImage');
    const previewContainer = document.getElementById('previewContainer');
    const analyzeButton = document.getElementById('analyzeButton');

    if (productImage) productImage.value = '';
    if (previewContainer) previewContainer.classList.add('hidden');
    if (analyzeButton) analyzeButton.disabled = true;
}

function analyzeProduct() {
    if (!selectedImage) {
        showToast('Please upload a product image first.');
        return;
    }

    const progress = document.getElementById('analysisProgress');
    const button = document.getElementById('analyzeButton');

    if (progress) progress.classList.remove('hidden');
    if (button) button.disabled = true;

    setTimeout(function () {
        const result = generateMockAnalysis();
        displayAnalysis(result);

        if (progress) progress.classList.add('hidden');
        const extractedSection = document.getElementById('extractedSection');
        if (extractedSection) extractedSection.classList.remove('hidden');
        extractedSection?.scrollIntoView({ behavior: 'smooth' });
    }, 1800);
}

function generateMockAnalysis() {
    return {
        productName: 'ABC Premium Rice',
        manufacturer: 'ABC Foods Pvt. Ltd.',
        mrp: '₹120.00',
        netQuantity: '5 kg',
        manufacturingDate: '08/2026',
        bestBefore: '6 Months',
        consumerCare: '1800-123-4567',
        countryOrigin: 'India',
        score: 88,
        status: 'WARNING',
        violations: [
            'Unit sale price declaration was not detected.',
            'Please verify the minimum font-size/readability requirement.'
        ]
    };
}

function displayAnalysis(result) {
    document.getElementById('productName').textContent = result.productName;
    document.getElementById('manufacturer').textContent = result.manufacturer;
    document.getElementById('mrp').textContent = result.mrp;
    document.getElementById('netQuantity').textContent = result.netQuantity;
    document.getElementById('manufacturingDate').textContent = result.manufacturingDate;
    document.getElementById('bestBefore').textContent = result.bestBefore;
    document.getElementById('consumerCare').textContent = result.consumerCare;
    document.getElementById('countryOrigin').textContent = result.countryOrigin;
    document.getElementById('complianceScore').textContent = result.score + '%';

    const status = document.getElementById('overallStatus');
    status.textContent = result.status;

    if (result.status === 'COMPLIANT') {
        status.style.background = '#dcfce7';
        status.style.color = '#166534';
    } else if (result.status === 'WARNING') {
        status.style.background = '#fef3c7';
        status.style.color = '#92400e';
    } else {
        status.style.background = '#fee2e2';
        status.style.color = '#991b1b';
    }

    const list = document.getElementById('violationsList');
    list.innerHTML = '';
    window.lastGeneratedViolations = Array.isArray(result.violations) ? result.violations.slice() : [];

    if (result.violations.length === 0) {
        list.innerHTML = '<div class="violation" style="background:#f0fdf4;border-color:#bbf7d0;color:#166534;">✓ No issues detected.</div>';
        return;
    }

    result.violations.forEach(function (item) {
        const div = document.createElement('div');
        div.className = 'violation';
        div.textContent = '⚠ ' + item;
        list.appendChild(div);
    });
}

function generateInspectionReport(result) {
    const lines = [
        'LegalMetrix Inspection Report',
        '===========================',
        'Product Name: ' + (result.productName || 'N/A'),
        'Manufacturer: ' + (result.manufacturer || 'N/A'),
        'MRP: ' + (result.mrp || 'N/A'),
        'Net Quantity: ' + (result.netQuantity || 'N/A'),
        'Manufacturing Date: ' + (result.manufacturingDate || 'N/A'),
        'Best Before: ' + (result.bestBefore || 'N/A'),
        'Consumer Care: ' + (result.consumerCare || 'N/A'),
        'Country of Origin: ' + (result.countryOrigin || 'N/A'),
        'Category: ' + (result.category || 'N/A'),
        'Compliance Score: ' + (result.score || '0%'),
        'Status: ' + (result.status || 'WARNING'),
        '',
        'Detected Issues:',
        (Array.isArray(result.violations) && result.violations.length ? result.violations.join('\n') : 'No issues detected.')
    ];

    return lines.join('\n');
}

function saveCurrentInspection() {
    const image = document.getElementById('previewImage')?.dataset.image || '';
    const result = {
        id: 'LM-' + Date.now(),
        productName: document.getElementById('productName').textContent,
        manufacturer: document.getElementById('manufacturer').textContent,
        mrp: document.getElementById('mrp').textContent,
        netQuantity: document.getElementById('netQuantity').textContent,
        manufacturingDate: document.getElementById('manufacturingDate').textContent,
        bestBefore: document.getElementById('bestBefore').textContent,
        consumerCare: document.getElementById('consumerCare').textContent,
        countryOrigin: document.getElementById('countryOrigin').textContent,
        score: document.getElementById('complianceScore').textContent,
        status: document.getElementById('overallStatus').textContent,
        category: document.getElementById('productCategory')?.value || 'Food / Grocery',
        image,
        report: generateInspectionReport({
            productName: document.getElementById('productName').textContent,
            manufacturer: document.getElementById('manufacturer').textContent,
            mrp: document.getElementById('mrp').textContent,
            netQuantity: document.getElementById('netQuantity').textContent,
            manufacturingDate: document.getElementById('manufacturingDate').textContent,
            bestBefore: document.getElementById('bestBefore').textContent,
            consumerCare: document.getElementById('consumerCare').textContent,
            countryOrigin: document.getElementById('countryOrigin').textContent,
            score: document.getElementById('complianceScore').textContent,
            status: document.getElementById('overallStatus').textContent,
            category: document.getElementById('productCategory')?.value || 'Food / Grocery',
            violations: Array.isArray(window.lastGeneratedViolations) ? window.lastGeneratedViolations : []
        }),
        date: new Date().toISOString()
    };

    saveInspection(result);
    showToast('Inspection saved successfully.');
    loadDashboardStats();
}

function loadDashboardStats() {
    const inspections = getInspections();
    const total = inspections.length;
    const compliant = inspections.filter(item => item.status === 'COMPLIANT').length;
    const violations = inspections.filter(item => item.status === 'NON_COMPLIANT').length;
    const rate = total === 0 ? 0 : Math.round((compliant / total) * 100);

    const totalScans = document.getElementById('totalScans');
    const compliantCount = document.getElementById('compliantCount');
    const violationCount = document.getElementById('violationCount');
    const complianceRate = document.getElementById('complianceRate');

    if (totalScans) totalScans.textContent = total;
    if (compliantCount) compliantCount.textContent = compliant;
    if (violationCount) violationCount.textContent = violations;
    if (complianceRate) complianceRate.textContent = rate + '%';
}

function restoreRetakeInspection() {
    const savedData = localStorage.getItem('legalMetrixRetakeInspection');
    if (!savedData) return;

    try {
        const inspection = JSON.parse(savedData);
        if (!inspection || !inspection.image) return;

        const previewImage = document.getElementById('previewImage');
        const previewContainer = document.getElementById('previewContainer');
        const selectedFileName = document.getElementById('selectedFileName');
        const analyzeButton = document.getElementById('analyzeButton');

        if (previewImage) {
            previewImage.src = inspection.image;
            previewImage.dataset.image = inspection.image;
        }

        if (previewContainer) previewContainer.classList.remove('hidden');
        if (selectedFileName) selectedFileName.textContent = inspection.productName || 'Retake photo';
        if (analyzeButton) analyzeButton.disabled = false;

        selectedImage = inspection.image;
        localStorage.removeItem('legalMetrixRetakeInspection');
        showToast('Previous inspection image loaded for retake.');
    } catch (error) {
        localStorage.removeItem('legalMetrixRetakeInspection');
    }
}

function resetScanner() {
    selectedImage = null;
    closeCamera();

    const previewContainer = document.getElementById('previewContainer');
    const extractedSection = document.getElementById('extractedSection');
    const productImage = document.getElementById('productImage');
    const analyzeButton = document.getElementById('analyzeButton');

    if (previewContainer) previewContainer.classList.add('hidden');
    if (extractedSection) extractedSection.classList.add('hidden');
    if (productImage) productImage.value = '';
    if (analyzeButton) analyzeButton.disabled = true;

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

let selectedImage = null;
