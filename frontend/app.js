let selectedImage = null;

document.addEventListener("DOMContentLoaded", function () {
    loadDashboardStats();

    const input = document.getElementById("productImage");
    const uploadArea = document.getElementById("uploadArea");
    const analyzeButton = document.getElementById("analyzeButton");
    const removeButton = document.getElementById("removeImage");

    if (input) {
        input.addEventListener("change", function (e) {
            if (e.target.files && e.target.files[0]) {
                handleImage(e.target.files[0]);
            }
        });
    }

    if (uploadArea) {
        uploadArea.addEventListener("dragover", function (e) {
            e.preventDefault();
            uploadArea.classList.add("dragging");
        });

        uploadArea.addEventListener("dragleave", function () {
            uploadArea.classList.remove("dragging");
        });

        uploadArea.addEventListener("drop", function (e) {
            e.preventDefault();
            uploadArea.classList.remove("dragging");
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleImage(e.dataTransfer.files[0]);
            }
        });
    }

    if (removeButton) {
        removeButton.addEventListener("click", removeImage);
    }

    if (analyzeButton) {
        analyzeButton.addEventListener("click", analyzeProduct);
    }

    const newScanBtn = document.getElementById("newScanButton");
    if (newScanBtn) newScanBtn.addEventListener("click", resetScanner);

    const saveResultBtn = document.getElementById("saveResultButton");
    if (saveResultBtn) saveResultBtn.addEventListener("click", saveCurrentInspection);
});

function handleImage(file) {
    if (!file.type.startsWith("image/")) {
        showToast("Please select a valid image file.");
        return;
    }

    selectedImage = file;

    const reader = new FileReader();
    reader.onload = function (event) {
        const preview = document.getElementById("previewImage");
        if (preview) {
            preview.src = event.target.result;
            preview.dataset.image = event.target.result;
        }

        const previewContainer = document.getElementById("previewContainer");
        if (previewContainer) previewContainer.classList.remove("hidden");

        const fileNameEl = document.getElementById("selectedFileName");
        if (fileNameEl) fileNameEl.textContent = file.name;

        const analyzeButton = document.getElementById("analyzeButton");
        if (analyzeButton) analyzeButton.disabled = false;
    };
    reader.readAsDataURL(file);
}

function removeImage() {
    selectedImage = null;
    const input = document.getElementById("productImage");
    if (input) input.value = "";

    const previewContainer = document.getElementById("previewContainer");
    if (previewContainer) previewContainer.classList.add("hidden");

    const analyzeButton = document.getElementById("analyzeButton");
    if (analyzeButton) analyzeButton.disabled = true;
}

async function analyzeProduct() {
    if (!selectedImage) {
        showToast("Please upload an image first.");
        return;
    }

    const progress = document.getElementById("analysisProgress");
    const button = document.getElementById("analyzeButton");

    if (progress) progress.classList.remove("hidden");
    if (button) {
        button.disabled = true;
        button.textContent = "Processing OCR & Legal Rules...";
    }

    try {
        const formData = new FormData();
        formData.append("file", selectedImage);

        const response = await fetch("http://127.0.0.1:8000/scan", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error("Backend error: " + response.status);
        }

        const data = await response.json();
        console.log("BACKEND RESULT:", data);

        const fields = data.extracted_fields || data.fields || {};
        const compliance = data.compliance_details || data.compliance || {};

        const getVal = (val) => {
            if (!val) return "-";
            if (typeof val === "object") return val.value || "-";
            return val;
        };

        const result = {
            productName: getVal(fields.product_name),
            manufacturer: getVal(fields.manufacturer),
            mrp: getVal(fields.mrp),
            netQuantity: getVal(fields.net_quantity),
            manufacturingDate: getVal(fields.manufacturing_date),
            bestBefore: getVal(fields.best_before),
            consumerCare: getVal(fields.consumer_care),
            countryOrigin: getVal(fields.country_of_origin),
            score: data.compliant ? 100 : 40,
            status: data.overall_status || (data.compliant ? "COMPLIANT" : "NON_COMPLIANT"),
            violations: data.violations || compliance.violations || [],
            reportUrl: data.report_url
        };

        displayAnalysis(result);

        if (progress) progress.classList.add("hidden");

        const extSection = document.getElementById("extractedSection");
        if (extSection) {
            extSection.classList.remove("hidden");
            extSection.scrollIntoView({ behavior: "smooth" });
        }

        showToast("Product analysis completed.");

    } catch (error) {
        console.error("Backend connection error:", error);
        if (progress) progress.classList.add("hidden");
        showToast("Could not connect to backend.");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Analyze Label";
        }
    }
}

function displayAnalysis(result) {
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    setEl("productName", result.productName);
    setEl("manufacturer", result.manufacturer);
    setEl("mrp", result.mrp);
    setEl("netQuantity", result.netQuantity);
    setEl("manufacturingDate", result.manufacturingDate);
    setEl("bestBefore", result.bestBefore);
    setEl("consumerCare", result.consumerCare);
    setEl("countryOrigin", result.countryOrigin);
    setEl("complianceScore", result.score + "%");

    const status = document.getElementById("overallStatus");
    if (status) {
        status.textContent = result.status;
        if (result.status === "COMPLIANT") {
            status.style.background = "#dcfce7";
            status.style.color = "#166534";
        } else {
            status.style.background = "#fee2e2";
            status.style.color = "#991b1b";
        }
    }

    const list = document.getElementById("violationsList");
    if (list) {
        list.innerHTML = "";
        if (result.violations.length === 0) {
            list.innerHTML = `
                <div class="violation" style="background:#f0fdf4; border-color:#bbf7d0; color:#166534; padding: 10px; border-radius: 6px;">
                    ✓ All mandatory declarations verified.
                </div>
            `;
        } else {
            result.violations.forEach((item) => {
                const div = document.createElement("div");
                div.className = "violation";
                div.textContent = "⚠ " + item;
                list.appendChild(div);
            });
        }
    }

    let pdfBtn = document.getElementById("downloadReportBtn");
    if (!pdfBtn && result.reportUrl) {
        const extSection = document.getElementById("extractedSection");
        if (extSection) {
            pdfBtn = document.createElement("a");
            pdfBtn.id = "downloadReportBtn";
            pdfBtn.className = "btn btn-primary";
            pdfBtn.style.display = "inline-block";
            pdfBtn.style.marginTop = "15px";
            pdfBtn.style.textDecoration = "none";
            pdfBtn.textContent = "📄 Download PDF Report";
            pdfBtn.target = "_blank";
            extSection.appendChild(pdfBtn);
        }
    }
    if (pdfBtn && result.reportUrl) {
        pdfBtn.href = result.reportUrl;
    }
}

function saveCurrentInspection() {
    const preview = document.getElementById("previewImage");
    const image = (preview && preview.dataset.image) || "";

    const result = {
        id: "LM-" + Date.now(),
        productName: (document.getElementById("productName") || {}).textContent || "-",
        manufacturer: (document.getElementById("manufacturer") || {}).textContent || "-",
        mrp: (document.getElementById("mrp") || {}).textContent || "-",
        status: (document.getElementById("overallStatus") || {}).textContent || "NON_COMPLIANT",
        image: image,
        date: new Date().toISOString()
    };

    saveInspection(result);
    showToast("Inspection saved successfully.");
    loadDashboardStats();
}

function loadDashboardStats() {
    const inspections = getInspections();
    const total = inspections.length;
    const compliant = inspections.filter((i) => i.status === "COMPLIANT").length;
    const violations = total - compliant;
    const rate = total === 0 ? 0 : Math.round((compliant / total) * 100);

    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    setEl("totalScans", total);
    setEl("compliantCount", compliant);
    setEl("violationCount", violations);
    setEl("complianceRate", rate + "%");
}

function resetScanner() {
    removeImage();
    const ext = document.getElementById("extractedSection");
    if (ext) ext.classList.add("hidden");
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function getInspections() {
    try {
        const data = localStorage.getItem("legalMetrixInspections");
        return data ? JSON.parse(data) : [];
    } catch {
        return [];
    }
}

function saveInspection(result) {
    const inspections = getInspections();
    inspections.push(result);
    localStorage.setItem("legalMetrixInspections", JSON.stringify(inspections));
}

function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.textContent = message;
    toast.style.display = "block";
    clearTimeout(showToast.timeoutId);
    showToast.timeoutId = setTimeout(() => {
        toast.style.display = "none";
    }, 2500);
}