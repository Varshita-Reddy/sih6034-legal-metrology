document.addEventListener('DOMContentLoaded', function () {
    const officerName = document.getElementById('officerName');
    const welcomeName = document.getElementById('welcomeName');
    const officerAvatar = document.getElementById('officerAvatar');

    if (officerName) {
        const stored = localStorage.getItem('legalMetrixOfficerName') || 'Officer';
        officerName.textContent = stored;
        if (welcomeName) welcomeName.textContent = stored;
        if (officerAvatar) officerAvatar.textContent = stored.charAt(0).toUpperCase();
    }

    loadDashboardStats();

    const input = document.getElementById('productImage');
    const uploadArea = document.getElementById('uploadArea');
    const analyzeButton = document.getElementById('analyzeButton');
    const removeButton = document.getElementById('removeImage');
    const newScanButton = document.getElementById('newScanButton');
    const saveResultButton = document.getElementById('saveResultButton');

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
});

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

function resetScanner() {
    selectedImage = null;

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
