function getCurrentOfficerName() {
    const storedName = localStorage.getItem('legalMetrixOfficerName');
    const cleanedName = (storedName || 'Officer').trim();
    return cleanedName || 'Officer';
}

function getOfficerHistoryKey() {
    const name = getCurrentOfficerName();
    const safeName = name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '') || 'officer';

    return 'legalMetrixInspections_' + safeName;
}

function getInspections() {
    try {
        const key = getOfficerHistoryKey();
        const data = localStorage.getItem(key);

        if (data) {
            const parsed = JSON.parse(data);
            return Array.isArray(parsed) ? parsed : [];
        }

        const legacyData = localStorage.getItem('legalMetrixInspections');
        if (legacyData) {
            const parsed = JSON.parse(legacyData);
            if (Array.isArray(parsed)) {
                localStorage.setItem(key, JSON.stringify(parsed));
                return parsed;
            }
        }

        return [];
    } catch (error) {
        return [];
    }
}

function saveInspection(result) {
    const inspections = getInspections();
    const officerName = getCurrentOfficerName();
    const inspection = {
        ...result,
        officerName: officerName
    };

    inspections.push(inspection);
    localStorage.setItem(getOfficerHistoryKey(), JSON.stringify(inspections));
    localStorage.setItem('legalMetrixInspections', JSON.stringify(inspections));
}

function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    toast.textContent = message;
    toast.style.display = 'block';

    clearTimeout(showToast.timeoutId);
    showToast.timeoutId = setTimeout(() => {
        toast.style.display = 'none';
    }, 2200);
}

function scrollToScanner() {
    const scanner = document.getElementById('scanner');
    if (scanner) {
        scanner.scrollIntoView({ behavior: 'smooth' });
    }
}
