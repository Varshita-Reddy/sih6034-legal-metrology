document.addEventListener('DOMContentLoaded', function () {
    const officerName = document.getElementById('officerName');
    const welcomeName = document.getElementById('welcomeName');
    const officerAvatar = document.getElementById('officerAvatar');

    if (officerName) {
        const stored = localStorage.getItem('legalMetrixOfficerName') || 'Officer';
        officerName.textContent = stored;

        if (welcomeName) {
            welcomeName.textContent = stored;
        }

        if (officerAvatar) {
            officerAvatar.textContent = stored.charAt(0).toUpperCase();
        }
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

    // PDF buttons
    const generateReportButton =
        document.getElementById('generateReportButton');

    const viewPdfButton =
        document.getElementById('viewPdfButton');

    const downloadPdfButton =
        document.getElementById('downloadPdfButton');


    // ================= IMAGE UPLOAD =================

    if (input) {
        input.addEventListener('change', function () {

            if (this.files && this.files[0]) {
                handleImage(this.files[0]);
            }

        });
    }


    // ================= DRAG AND DROP =================

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

            if (file) {
                handleImage(file);
            }

        });

    }


    // ================= EXISTING BUTTONS =================

    if (removeButton) {
        removeButton.addEventListener('click', removeImage);
    }

    if (analyzeButton) {
        analyzeButton.addEventListener('click', analyzeProduct);
    }

    if (newScanButton) {
        newScanButton.addEventListener('click', resetScanner);
    }

    if (saveResultButton) {
        saveResultButton.addEventListener(
            'click',
            saveCurrentInspection
        );
    }

    if (cameraButton) {
        cameraButton.addEventListener('click', openCamera);
    }

    if (captureButton) {
        captureButton.addEventListener('click', captureImage);
    }

    if (closeCameraButton) {
        closeCameraButton.addEventListener('click', closeCamera);
    }


    // ================= PDF BUTTONS =================

    if (generateReportButton) {

        generateReportButton.addEventListener(
            'click',
            generatePdfReport
        );

    }

    if (viewPdfButton) {

        viewPdfButton.addEventListener(
            'click',
            viewGeneratedPdf
        );

    }

    if (downloadPdfButton) {

        downloadPdfButton.addEventListener(
            'click',
            downloadGeneratedPdf
        );

    }

});


// =====================================================
// CAMERA
// =====================================================

let cameraStream = null;


// =====================================================
// PDF STATE
// =====================================================

let generatedPdfBlob = null;

let generatedPdfUrl = null;


// =====================================================
// CAMERA FUNCTIONS
// =====================================================

async function openCamera() {

    const cameraPanel =
        document.getElementById('cameraPanel');

    const cameraPreview =
        document.getElementById('cameraPreview');

    const cameraMessage =
        document.getElementById('cameraMessage');

    const captureButton =
        document.getElementById('captureButton');


    if (
        !navigator.mediaDevices ||
        !navigator.mediaDevices.getUserMedia
    ) {

        showToast(
            'Camera access is not supported by this browser.'
        );

        return;
    }


    try {

        cameraStream =
            await navigator.mediaDevices.getUserMedia({

                video: {
                    facingMode: {
                        ideal: 'environment'
                    }
                },

                audio: false

            });


        cameraPreview.srcObject =
            cameraStream;


        cameraPanel.classList.remove('hidden');

        cameraPanel.setAttribute(
            'aria-hidden',
            'false'
        );


        cameraMessage.textContent =
            'Position the product label inside the frame.';


        captureButton.disabled = false;


    } catch (error) {

        cameraMessage.textContent =
            'Camera access was blocked. Check browser permissions and try again.';

        showToast(
            'Unable to access the camera.'
        );

    }

}


// =====================================================
// CAPTURE IMAGE
// =====================================================

function captureImage() {

    const cameraPreview =
        document.getElementById('cameraPreview');


    if (
        !cameraStream ||
        !cameraPreview.videoWidth
    ) {

        showToast(
            'Camera is not ready yet.'
        );

        return;
    }


    const canvas =
        document.createElement('canvas');


    canvas.width =
        cameraPreview.videoWidth;


    canvas.height =
        cameraPreview.videoHeight;


    canvas
        .getContext('2d')
        .drawImage(
            cameraPreview,
            0,
            0
        );


    canvas.toBlob(
        function (blob) {

            if (blob) {

                handleImage(
                    new File(
                        [blob],
                        'camera-capture.jpg',
                        {
                            type: 'image/jpeg'
                        }
                    )
                );

                closeCamera();

            } else {

                showToast(
                    'Unable to capture an image.'
                );

            }

        },
        'image/jpeg',
        0.92
    );

}


// =====================================================
// CLOSE CAMERA
// =====================================================

function closeCamera() {

    const cameraPanel =
        document.getElementById('cameraPanel');

    const cameraPreview =
        document.getElementById('cameraPreview');


    if (cameraStream) {

        cameraStream
            .getTracks()
            .forEach(function (track) {

                track.stop();

            });


        cameraStream = null;

    }


    if (cameraPreview) {
        cameraPreview.srcObject = null;
    }


    if (cameraPanel) {

        cameraPanel.classList.add('hidden');

        cameraPanel.setAttribute(
            'aria-hidden',
            'true'
        );

    }

}


// =====================================================
// IMAGE HANDLING
// =====================================================

function handleImage(file) {

    if (!file.type.startsWith('image/')) {

        showToast(
            'Please select an image file.'
        );

        return;
    }


    if (file.size > 10 * 1024 * 1024) {

        showToast(
            'Image must be smaller than 10 MB.'
        );

        return;
    }


    selectedImage = file;


    const reader =
        new FileReader();


    reader.onload = function (event) {

        const preview =
            document.getElementById('previewImage');

        const previewContainer =
            document.getElementById('previewContainer');

        const selectedFileName =
            document.getElementById('selectedFileName');

        const analyzeButton =
            document.getElementById('analyzeButton');


        if (preview) {

            preview.src =
                event.target.result;

            preview.dataset.image =
                event.target.result;

        }


        if (previewContainer) {

            previewContainer.classList.remove(
                'hidden'
            );

        }


        if (selectedFileName) {

            selectedFileName.textContent =
                file.name;

        }


        if (analyzeButton) {

            analyzeButton.disabled =
                false;

        }

    };


    reader.readAsDataURL(file);

}


// =====================================================
// REMOVE IMAGE
// =====================================================

function removeImage() {

    selectedImage = null;


    const productImage =
        document.getElementById('productImage');

    const previewContainer =
        document.getElementById('previewContainer');

    const analyzeButton =
        document.getElementById('analyzeButton');


    if (productImage) {
        productImage.value = '';
    }


    if (previewContainer) {

        previewContainer.classList.add(
            'hidden'
        );

    }


    if (analyzeButton) {

        analyzeButton.disabled =
            true;

    }

}


// =====================================================
// ANALYZE PRODUCT
// =====================================================

function analyzeProduct() {

    if (!selectedImage) {

        showToast(
            'Please upload a product image first.'
        );

        return;
    }


    const progress =
        document.getElementById(
            'analysisProgress'
        );

    const button =
        document.getElementById(
            'analyzeButton'
        );


    if (progress) {

        progress.classList.remove(
            'hidden'
        );

    }


    if (button) {

        button.disabled =
            true;

    }


    setTimeout(function () {

        const result =
            generateMockAnalysis();


        displayAnalysis(result);


        if (progress) {

            progress.classList.add(
                'hidden'
            );

        }


        const extractedSection =
            document.getElementById(
                'extractedSection'
            );


        if (extractedSection) {

            extractedSection.classList.remove(
                'hidden'
            );

            extractedSection.scrollIntoView({
                behavior: 'smooth'
            });

        }

    }, 1800);

}


// =====================================================
// MOCK ANALYSIS
// =====================================================

function generateMockAnalysis() {

    return {

        productName:
            'ABC Premium Rice',

        manufacturer:
            'ABC Foods Pvt. Ltd.',

        mrp:
            '₹120.00',

        netQuantity:
            '5 kg',

        manufacturingDate:
            '08/2026',

        bestBefore:
            '6 Months',

        consumerCare:
            '1800-123-4567',

        countryOrigin:
            'India',

        score:
            88,

        status:
            'WARNING',

        violations: [

            'Unit sale price declaration was not detected.',

            'Please verify the minimum font-size/readability requirement.'

        ]

    };

}


// =====================================================
// DISPLAY ANALYSIS
// =====================================================

function displayAnalysis(result) {

    document.getElementById(
        'productName'
    ).textContent =
        result.productName;


    document.getElementById(
        'manufacturer'
    ).textContent =
        result.manufacturer;


    document.getElementById(
        'mrp'
    ).textContent =
        result.mrp;


    document.getElementById(
        'netQuantity'
    ).textContent =
        result.netQuantity;


    document.getElementById(
        'manufacturingDate'
    ).textContent =
        result.manufacturingDate;


    document.getElementById(
        'bestBefore'
    ).textContent =
        result.bestBefore;


    document.getElementById(
        'consumerCare'
    ).textContent =
        result.consumerCare;


    document.getElementById(
        'countryOrigin'
    ).textContent =
        result.countryOrigin;


    document.getElementById(
        'complianceScore'
    ).textContent =
        result.score + '%';


    const status =
        document.getElementById(
            'overallStatus'
        );


    status.textContent =
        result.status;


    if (result.status === 'COMPLIANT') {

        status.style.background =
            '#dcfce7';

        status.style.color =
            '#166534';

    } else if (
        result.status === 'WARNING'
    ) {

        status.style.background =
            '#fef3c7';

        status.style.color =
            '#92400e';

    } else {

        status.style.background =
            '#fee2e2';

        status.style.color =
            '#991b1b';

    }


    const list =
        document.getElementById(
            'violationsList'
        );


    list.innerHTML = '';


    window.lastGeneratedViolations =
        Array.isArray(result.violations)
            ? result.violations.slice()
            : [];


    if (
        !Array.isArray(result.violations) ||
        result.violations.length === 0
    ) {

        list.innerHTML =
            '<div class="violation" style="background:#f0fdf4;border-color:#bbf7d0;color:#166534;">✓ No issues detected.</div>';

        return;

    }


    result.violations.forEach(
        function (item) {

            const div =
                document.createElement(
                    'div'
                );


            div.className =
                'violation';


            div.textContent =
                '⚠ ' + item;


            list.appendChild(div);

        }
    );

}


// =====================================================
// OLD TEXT REPORT
// =====================================================

function generateInspectionReport(result) {

    const lines = [

        'LegalMetrix Inspection Report',

        '===========================',

        'Product Name: ' +
            (result.productName || 'N/A'),

        'Manufacturer: ' +
            (result.manufacturer || 'N/A'),

        'MRP: ' +
            (result.mrp || 'N/A'),

        'Net Quantity: ' +
            (result.netQuantity || 'N/A'),

        'Manufacturing Date: ' +
            (result.manufacturingDate || 'N/A'),

        'Best Before: ' +
            (result.bestBefore || 'N/A'),

        'Consumer Care: ' +
            (result.consumerCare || 'N/A'),

        'Country of Origin: ' +
            (result.countryOrigin || 'N/A'),

        'Category: ' +
            (result.category || 'N/A'),

        'Compliance Score: ' +
            (result.score || '0%'),

        'Status: ' +
            (result.status || 'WARNING'),

        '',

        'Detected Issues:',

        (
            Array.isArray(result.violations) &&
            result.violations.length
        )
            ? result.violations.join('\n')
            : 'No issues detected.'

    ];


    return lines.join('\n');

}


// =====================================================
// SAVE INSPECTION
// =====================================================

function saveCurrentInspection() {

    const image =
        document
            .getElementById('previewImage')
            ?.dataset.image || '';


    const result = {

        id:
            'LM-' + Date.now(),

        productName:
            document.getElementById(
                'productName'
            ).textContent,

        manufacturer:
            document.getElementById(
                'manufacturer'
            ).textContent,

        mrp:
            document.getElementById(
                'mrp'
            ).textContent,

        netQuantity:
            document.getElementById(
                'netQuantity'
            ).textContent,

        manufacturingDate:
            document.getElementById(
                'manufacturingDate'
            ).textContent,

        bestBefore:
            document.getElementById(
                'bestBefore'
            ).textContent,

        consumerCare:
            document.getElementById(
                'consumerCare'
            ).textContent,

        countryOrigin:
            document.getElementById(
                'countryOrigin'
            ).textContent,

        score:
            document.getElementById(
                'complianceScore'
            ).textContent,

        status:
            document.getElementById(
                'overallStatus'
            ).textContent,

        category:
            document.getElementById(
                'productCategory'
            )?.value ||
            'Food / Grocery',

        image,

        report:
            generateInspectionReport({

                productName:
                    document.getElementById(
                        'productName'
                    ).textContent,

                manufacturer:
                    document.getElementById(
                        'manufacturer'
                    ).textContent,

                mrp:
                    document.getElementById(
                        'mrp'
                    ).textContent,

                netQuantity:
                    document.getElementById(
                        'netQuantity'
                    ).textContent,

                manufacturingDate:
                    document.getElementById(
                        'manufacturingDate'
                    ).textContent,

                bestBefore:
                    document.getElementById(
                        'bestBefore'
                    ).textContent,

                consumerCare:
                    document.getElementById(
                        'consumerCare'
                    ).textContent,

                countryOrigin:
                    document.getElementById(
                        'countryOrigin'
                    ).textContent,

                score:
                    document.getElementById(
                        'complianceScore'
                    ).textContent,

                status:
                    document.getElementById(
                        'overallStatus'
                    ).textContent,

                category:
                    document.getElementById(
                        'productCategory'
                    )?.value ||
                    'Food / Grocery',

                violations:
                    Array.isArray(
                        window.lastGeneratedViolations
                    )
                        ? window.lastGeneratedViolations
                        : []

            }),

        date:
            new Date().toISOString()

    };


    saveInspection(result);

    showToast(
        'Inspection saved successfully.'
    );

    loadDashboardStats();

}


// =====================================================
// PDF: BUILD COMPLIANCE RESULT
// =====================================================

function buildComplianceResultForPdf() {

    const productName =
        document.getElementById(
            'productName'
        )?.textContent || 'N/A';


    const manufacturer =
        document.getElementById(
            'manufacturer'
        )?.textContent || 'N/A';


    const mrp =
        document.getElementById(
            'mrp'
        )?.textContent || 'N/A';


    const netQuantity =
        document.getElementById(
            'netQuantity'
        )?.textContent || 'N/A';


    const manufacturingDate =
        document.getElementById(
            'manufacturingDate'
        )?.textContent || 'N/A';


    const bestBefore =
        document.getElementById(
            'bestBefore'
        )?.textContent || 'N/A';


    const consumerCare =
        document.getElementById(
            'consumerCare'
        )?.textContent || 'N/A';


    const countryOrigin =
        document.getElementById(
            'countryOrigin'
        )?.textContent || 'N/A';


    const scoreText =
        document.getElementById(
            'complianceScore'
        )?.textContent || '0';


    const score =
        Number(
            String(scoreText)
                .replace('%', '')
                .trim()
        ) || 0;


    const status =
        document.getElementById(
            'overallStatus'
        )?.textContent || 'WARNING';


    const category =
        document.getElementById(
            'productCategory'
        )?.value ||
        'Food / Grocery';


    const violations =
        Array.isArray(
            window.lastGeneratedViolations
        )
            ? window.lastGeneratedViolations
            : [];


    return {

        inspection_id:
            'LM-' + Date.now(),

        product: {

            product_name:
                productName,

            brand_name:
                'N/A',

            common_generic_name:
                productName,

            product_category:
                category,

            product_subcategory:
                category,

            manufacturer_name:
                manufacturer,

            manufacturer_address:
                'N/A',

            net_quantity:
                netQuantity,

            mrp:
                mrp,

            manufacturing_date:
                manufacturingDate,

            consumer_care:
                consumerCare,

            best_before:
                bestBefore,

            country_of_origin:
                countryOrigin

        },

        status:
            status,

        compliance_score:
            score,

        violations:
            violations.map(
                function (message) {

                    return {

                        field:
                            'compliance',

                        rule_id:
                            'LM-RULE',

                        severity:
                            'MEDIUM',

                        message:
                            message,

                        evidence:
                            null

                    };

                }
            ),

        checked_rules: [

            'common_generic_name',

            'manufacturer_name',

            'manufacturer_address',

            'net_quantity',

            'manufacturing_date',

            'mrp',

            'consumer_care',

            'country_of_origin'

        ],

        created_at:
            new Date().toISOString()

    };

}


// =====================================================
// PDF: GENERATE
// =====================================================

// =====================================================
// PDF: GENERATE
// =====================================================

async function generatePdfReport() {

    const button =
        document.getElementById(
            'generateReportButton'
        );

    const viewButton =
        document.getElementById(
            'viewPdfButton'
        );

    const downloadButton =
        document.getElementById(
            'downloadPdfButton'
        );

    if (!document.getElementById('productName')) {

        showToast(
            'Please analyze a product first.'
        );

        return;
    }

    try {

        if (button) {

            button.disabled = true;

            button.textContent =
                'Generating PDF...';

        }

        const complianceResult =
            buildComplianceResultForPdf();

        console.log(
            'Sending compliance data:',
            complianceResult
        );

        const response =
            await fetch(
                'http://127.0.0.1:8000/api/report/generate',
                {
                    method: 'POST',

                    mode: 'cors',

                    headers: {
                        'Content-Type':
                            'application/json',

                        'Accept':
                            'application/pdf'
                    },

                    body:
                        JSON.stringify(
                            complianceResult
                        )
                }
            );

        console.log(
            'PDF API response:',
            response.status,
            response.statusText
        );

        if (!response.ok) {

            let errorMessage =
                'Unable to generate PDF.';

            try {

                const contentType =
                    response.headers.get(
                        'content-type'
                    );

                if (
                    contentType &&
                    contentType.includes(
                        'application/json'
                    )
                ) {

                    const errorData =
                        await response.json();

                    if (
                        errorData &&
                        errorData.detail
                    ) {

                        errorMessage =
                            Array.isArray(
                                errorData.detail
                            )
                                ? errorData.detail
                                    .map(
                                        item =>
                                            item.msg ||
                                            String(item)
                                    )
                                    .join(', ')
                                : String(
                                    errorData.detail
                                );
                    }
                }

            } catch (error) {

                console.error(
                    'Error reading server error:',
                    error
                );
            }

            throw new Error(
                errorMessage
            );
        }

        generatedPdfBlob =
            await response.blob();

        console.log(
            'PDF blob received:',
            generatedPdfBlob.size,
            generatedPdfBlob.type
        );

        if (
            !generatedPdfBlob ||
            generatedPdfBlob.size === 0
        ) {

            throw new Error(
                'The server returned an empty PDF.'
            );
        }

        if (generatedPdfUrl) {

            URL.revokeObjectURL(
                generatedPdfUrl
            );
        }

        generatedPdfUrl =
            URL.createObjectURL(
                generatedPdfBlob
            );

        if (viewButton) {

            viewButton.style.display =
                'inline-block';

        }

        if (downloadButton) {

            downloadButton.style.display =
                'inline-block';

        }

        showToast(
            'PDF report generated successfully.'
        );

    } catch (error) {

        console.error(
            'PDF generation error:',
            error
        );

        showToast(
            error.message ||
            'Failed to generate PDF.'
        );

    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                'Generate Report';
        }
    }
}
  


// =====================================================
// PDF: VIEW
// =====================================================

function viewGeneratedPdf() {

    if (!generatedPdfUrl) {

        showToast(
            'Please generate the PDF first.'
        );

        return;

    }


    window.open(
        generatedPdfUrl,
        '_blank'
    );

}


// =====================================================
// PDF: DOWNLOAD
// =====================================================

function downloadGeneratedPdf() {

    if (!generatedPdfUrl) {

        showToast(
            'Please generate the PDF first.'
        );

        return;

    }


    const link =
        document.createElement('a');


    link.href =
        generatedPdfUrl;


    link.download =
        'compliance_report.pdf';


    document.body.appendChild(
        link
    );


    link.click();


    link.remove();


    showToast(
        'PDF download started.'
    );

}


// =====================================================
// DASHBOARD STATS
// =====================================================

function loadDashboardStats() {

    const inspections =
        getInspections();


    const total =
        inspections.length;


    const compliant =
        inspections.filter(
            item =>
                item.status ===
                'COMPLIANT'
        ).length;


    const violations =
        inspections.filter(
            item =>
                item.status ===
                'NON_COMPLIANT'
        ).length;


    const rate =
        total === 0
            ? 0
            : Math.round(
                (compliant / total) * 100
            );


    const totalScans =
        document.getElementById(
            'totalScans'
        );


    const compliantCount =
        document.getElementById(
            'compliantCount'
        );


    const violationCount =
        document.getElementById(
            'violationCount'
        );


    const complianceRate =
        document.getElementById(
            'complianceRate'
        );


    if (totalScans) {

        totalScans.textContent =
            total;

    }


    if (compliantCount) {

        compliantCount.textContent =
            compliant;

    }


    if (violationCount) {

        violationCount.textContent =
            violations;

    }


    if (complianceRate) {

        complianceRate.textContent =
            rate + '%';

    }

}


// =====================================================
// RESTORE RETAKE INSPECTION
// =====================================================

function restoreRetakeInspection() {

    const savedData =
        localStorage.getItem(
            'legalMetrixRetakeInspection'
        );


    if (!savedData) {
        return;
    }


    try {

        const inspection =
            JSON.parse(savedData);


        if (
            !inspection ||
            !inspection.image
        ) {

            return;

        }


        const previewImage =
            document.getElementById(
                'previewImage'
            );


        const previewContainer =
            document.getElementById(
                'previewContainer'
            );


        const selectedFileName =
            document.getElementById(
                'selectedFileName'
            );


        const analyzeButton =
            document.getElementById(
                'analyzeButton'
            );


        if (previewImage) {

            previewImage.src =
                inspection.image;

            previewImage.dataset.image =
                inspection.image;

        }


        if (previewContainer) {

            previewContainer.classList.remove(
                'hidden'
            );

        }


        if (selectedFileName) {

            selectedFileName.textContent =
                inspection.productName ||
                'Retake photo';

        }


        if (analyzeButton) {

            analyzeButton.disabled =
                false;

        }


        selectedImage =
            inspection.image;


        localStorage.removeItem(
            'legalMetrixRetakeInspection'
        );


        showToast(
            'Previous inspection image loaded for retake.'
        );


    } catch (error) {

        localStorage.removeItem(
            'legalMetrixRetakeInspection'
        );

    }

}


// =====================================================
// RESET SCANNER
// =====================================================

function resetScanner() {

    selectedImage = null;

    closeCamera();


    const previewContainer =
        document.getElementById(
            'previewContainer'
        );


    const extractedSection =
        document.getElementById(
            'extractedSection'
        );


    const productImage =
        document.getElementById(
            'productImage'
        );


    const analyzeButton =
        document.getElementById(
            'analyzeButton'
        );


    const generateReportButton =
        document.getElementById(
            'generateReportButton'
        );


    const viewPdfButton =
        document.getElementById(
            'viewPdfButton'
        );


    const downloadPdfButton =
        document.getElementById(
            'downloadPdfButton'
        );


    if (previewContainer) {

        previewContainer.classList.add(
            'hidden'
        );

    }


    if (extractedSection) {

        extractedSection.classList.add(
            'hidden'
        );

    }


    if (productImage) {

        productImage.value = '';

    }


    if (analyzeButton) {

        analyzeButton.disabled =
            true;

    }


    // Reset PDF state

    generatedPdfBlob = null;


    if (generatedPdfUrl) {

        URL.revokeObjectURL(
            generatedPdfUrl
        );

        generatedPdfUrl = null;

    }


    if (generateReportButton) {

        generateReportButton.disabled =
            false;

        generateReportButton.textContent =
            'Generate Report';

    }


    if (viewPdfButton) {

        viewPdfButton.style.display =
            'none';

    }


    if (downloadPdfButton) {

        downloadPdfButton.style.display =
            'none';

    }


    window.scrollTo({

        top: 0,

        behavior: 'smooth'

    });

}




let selectedImage = null;