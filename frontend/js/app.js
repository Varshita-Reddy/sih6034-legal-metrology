function getInspections() {
    try {
        const data = localStorage.getItem('legalMetrixInspections');
        return data ? JSON.parse(data) : [];
    } catch (error) {
        return [];
    }
}

function saveInspection(result) {
    const inspections = getInspections();
    inspections.push(result);
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
