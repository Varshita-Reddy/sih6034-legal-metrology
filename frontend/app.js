let selectedImage = null;


/* ==========================================
   PAGE INITIALIZATION
========================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        loadDashboardStats();


        const input =
            document.getElementById(
                "productImage"
            );


        const uploadArea =
            document.getElementById(
                "uploadArea"
            );


        const analyzeButton =
            document.getElementById(
                "analyzeButton"
            );


        const removeButton =
            document.getElementById(
                "removeImage"
            );


        input.addEventListener(
            "change",
            function () {

                if (
                    this.files &&
                    this.files[0]
                ) {

                    handleImage(
                        this.files[0]
                    );

                }

            }
        );


        removeButton.addEventListener(
            "click",
            removeImage
        );


        analyzeButton.addEventListener(
            "click",
            analyzeProduct
        );


        /* DRAG AND DROP */

        uploadArea.addEventListener(
            "dragover",
            function (event) {

                event.preventDefault();

                uploadArea.classList.add(
                    "dragging"
                );

            }
        );


        uploadArea.addEventListener(
            "dragleave",
            function () {

                uploadArea.classList.remove(
                    "dragging"
                );

            }
        );


        uploadArea.addEventListener(
            "drop",
            function (event) {

                event.preventDefault();

                uploadArea.classList.remove(
                    "dragging"
                );


                const file =
                    event
                        .dataTransfer
                        .files[0];


                if (file) {

                    handleImage(
                        file
                    );

                }

            }
        );


        document
            .getElementById(
                "newScanButton"
            )
            .addEventListener(
                "click",
                resetScanner
            );


        document
            .getElementById(
                "saveResultButton"
            )
            .addEventListener(
                "click",
                saveCurrentInspection
            );

    }
);


/* ==========================================
   IMAGE HANDLING
========================================== */

function handleImage(file) {

    if (
        !file.type.startsWith(
            "image/"
        )
    ) {

        showToast(
            "Please select an image file."
        );

        return;

    }


    if (
        file.size >
        10 * 1024 * 1024
    ) {

        showToast(
            "Image must be smaller than 10 MB."
        );

        return;

    }


    selectedImage =
        file;


    const reader =
        new FileReader();


    reader.onload =
        function (event) {

            const preview =
                document.getElementById(
                    "previewImage"
                );


            preview.src =
                event.target.result;


            preview.dataset.image =
                event.target.result;


            document
                .getElementById(
                    "previewContainer"
                )
                .classList.remove(
                    "hidden"
                );


            document
                .getElementById(
                    "selectedFileName"
                )
                .textContent =
                file.name;


            document
                .getElementById(
                    "analyzeButton"
                )
                .disabled =
                false;

        };


    reader.readAsDataURL(
        file
    );

}


/* ==========================================
   REMOVE IMAGE
========================================== */

function removeImage() {

    selectedImage =
        null;


    document
        .getElementById(
            "productImage"
        )
        .value =
        "";


    document
        .getElementById(
            "previewContainer"
        )
        .classList.add(
            "hidden"
        );


    document
        .getElementById(
            "analyzeButton"
        )
        .disabled =
        true;

}


/* ==========================================
   ANALYZE PRODUCT
========================================== */

function analyzeProduct() {

    if (!selectedImage) {

        showToast(
            "Please upload a product image first."
        );

        return;

    }


    const progress =
        document.getElementById(
            "analysisProgress"
        );


    progress.classList.remove(
        "hidden"
    );


    const button =
        document.getElementById(
            "analyzeButton"
        );


    button.disabled =
        true;


    /*
       THIS IS CURRENTLY A MOCK ANALYSIS.

       Later replace this function with:

       fetch("/api/analyze", {
           method: "POST",
           body: formData
       })

       The backend can then use:
       OCR + AI + Legal Metrology rules.
    */


    setTimeout(
        function () {

            const result =
                generateMockAnalysis();


            displayAnalysis(
                result
            );


            progress.classList.add(
                "hidden"
            );


            document
                .getElementById(
                    "extractedSection"
                )
                .classList.remove(
                    "hidden"
                );


            document
                .getElementById(
                    "extractedSection"
                )
                .scrollIntoView({
                    behavior:
                        "smooth"
                });


        },
        1800
    );

}


/* ==========================================
   MOCK OCR / AI RESULT
========================================== */

function generateMockAnalysis() {

    /*
        These values simulate what your
        future OCR + AI backend will return.
    */


    return {

        productName:
            "ABC Premium Rice",

        manufacturer:
            "ABC Foods Pvt. Ltd.",

        mrp:
            "₹120.00",

        netQuantity:
            "5 kg",

        manufacturingDate:
            "08/2026",

        bestBefore:
            "6 Months",

        consumerCare:
            "1800-123-4567",

        countryOrigin:
            "India",

        score:
            88,

        status:
            "WARNING",

        violations: [

            "Unit sale price declaration was not detected.",

            "Please verify the minimum font-size/readability requirement."

        ]

    };

}


/* ==========================================
   DISPLAY RESULT
========================================== */

function displayAnalysis(
    result
) {

    document.getElementById(
        "productName"
    ).textContent =
        result.productName;


    document.getElementById(
        "manufacturer"
    ).textContent =
        result.manufacturer;


    document.getElementById(
        "mrp"
    ).textContent =
        result.mrp;


    document.getElementById(
        "netQuantity"
    ).textContent =
        result.netQuantity;


    document.getElementById(
        "manufacturingDate"
    ).textContent =
        result.manufacturingDate;


    document.getElementById(
        "bestBefore"
    ).textContent =
        result.bestBefore;


    document.getElementById(
        "consumerCare"
    ).textContent =
        result.consumerCare;


    document.getElementById(
        "countryOrigin"
    ).textContent =
        result.countryOrigin;


    document.getElementById(
        "complianceScore"
    ).textContent =
        result.score + "%";


    const status =
        document.getElementById(
            "overallStatus"
        );


    status.textContent =
        result.status;


    /* STATUS COLOR */

    if (
        result.status ===
        "COMPLIANT"
    ) {

        status.style.background =
            "#dcfce7";

        status.style.color =
            "#166534";

    }

    else if (
        result.status ===
        "WARNING"
    ) {

        status.style.background =
            "#fef3c7";

        status.style.color =
            "#92400e";

    }

    else {

        status.style.background =
            "#fee2e2";

        status.style.color =
            "#991b1b";

    }


    /* VIOLATIONS */

    const list =
        document.getElementById(
            "violationsList"
        );


    list.innerHTML =
        "";


    if (
        result.violations.length ===
        0
    ) {

        list.innerHTML = `

            <div class="violation"
                 style="
                    background:#f0fdf4;
                    border-color:#bbf7d0;
                    color:#166534;
                 ">

                ✓ No issues detected.

            </div>

        `;

        return;

    }


    result.violations.forEach(
        function (item) {

            const div =
                document.createElement(
                    "div"
                );


            div.className =
                "violation";


            div.textContent =
                "⚠ " + item;


            list.appendChild(
                div
            );

        }
    );

}


/* ==========================================
   SAVE RESULT
========================================== */

function saveCurrentInspection() {

    const image =
        document.getElementById(
            "previewImage"
        ).dataset.image || "";


    const result = {

        id:
            "LM-" +
            Date.now(),

        productName:
            document.getElementById(
                "productName"
            ).textContent,

        manufacturer:
            document.getElementById(
                "manufacturer"
            ).textContent,

        mrp:
            document.getElementById(
                "mrp"
            ).textContent,

        netQuantity:
            document.getElementById(
                "netQuantity"
            ).textContent,

        manufacturingDate:
            document.getElementById(
                "manufacturingDate"
            ).textContent,

        bestBefore:
            document.getElementById(
                "bestBefore"
            ).textContent,

        consumerCare:
            document.getElementById(
                "consumerCare"
            ).textContent,

        countryOrigin:
            document.getElementById(
                "countryOrigin"
            ).textContent,

        score:
            document.getElementById(
                "complianceScore"
            ).textContent,

        status:
            document.getElementById(
                "overallStatus"
            ).textContent,

        category:
            document.getElementById(
                "productCategory"
            ).value,

        image,

        date:
            new Date().toISOString()

    };


    saveInspection(
        result
    );


    showToast(
        "Inspection saved successfully."
    );


    loadDashboardStats();

}


/* ==========================================
   DASHBOARD STATS
========================================== */

function loadDashboardStats() {

    const inspections =
        getInspections();


    const total =
        inspections.length;


    const compliant =
        inspections.filter(
            item =>
                item.status ===
                "COMPLIANT"
        ).length;


    const violations =
        inspections.filter(
            item =>
                item.status ===
                "NON_COMPLIANT"
        ).length;


    const rate =
        total === 0
            ? 0
            : Math.round(
                (
                    compliant /
                    total
                ) * 100
            );


    document.getElementById(
        "totalScans"
    ).textContent =
        total;


    document.getElementById(
        "compliantCount"
    ).textContent =
        compliant;


    document.getElementById(
        "violationCount"
    ).textContent =
        violations;


    document.getElementById(
        "complianceRate"
    ).textContent =
        rate + "%";

}


/* ==========================================
   RESET
========================================== */

function resetScanner() {

    selectedImage =
        null;


    document
        .getElementById(
            "previewContainer"
        )
        .classList.add(
            "hidden"
        );


    document
        .getElementById(
            "extractedSection"
        )
        .classList.add(
            "hidden"
        );


    document
        .getElementById(
            "productImage"
        )
        .value =
        "";


    document
        .getElementById(
            "analyzeButton"
        )
        .disabled =
        true;


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


/* ==========================================
   SCROLL
========================================== */

function scrollToScanner() {

    document
        .getElementById(
            "scanner"
        )
        .scrollIntoView({
            behavior:
                "smooth"
        });

}


/* ==========================================
   STORAGE HELPERS
========================================== */

function getInspections() {

    try {

        const data =
            localStorage.getItem(
                "legalMetrixInspections"
            );

        return data ? JSON.parse(data) : [];

    } catch (error) {

        return [];

    }

}


function saveInspection(result) {

    const inspections =
        getInspections();

    inspections.push(result);

    localStorage.setItem(
        "legalMetrixInspections",
        JSON.stringify(inspections)
    );

}


function showToast(message) {

    const toast =
        document.getElementById(
            "toast"
        );

    if (!toast) {
        return;
    }

    toast.textContent = message;
    toast.style.display = "block";

    clearTimeout(showToast.timeoutId);

    showToast.timeoutId =
        setTimeout(function () {
            toast.style.display = "none";
        }, 2200);

}
