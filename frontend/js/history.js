document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const historyTable = document.getElementById('historyTable');
    const emptyHistory = document.getElementById('emptyHistory');

    function renderHistory() {
        const inspections = getInspections();
        const searchValue = (searchInput?.value || '').trim().toLowerCase();
        const filterValue = statusFilter?.value || 'ALL';

        const filtered = inspections.filter(item => {
            const matchesSearch = !searchValue || (item.productName || '').toLowerCase().includes(searchValue);
            const matchesStatus = filterValue === 'ALL' || item.status === filterValue;
            return matchesSearch && matchesStatus;
        });

        if (!historyTable) return;
        historyTable.innerHTML = '';

        if (!filtered.length) {
            if (emptyHistory) emptyHistory.style.display = 'block';
            return;
        }

        if (emptyHistory) emptyHistory.style.display = 'none';

        filtered.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${item.productName || 'Unknown'}</td>
                <td>${item.mrp || '-'}</td>
                <td>${item.manufacturingDate || '-'}</td>
                <td>${item.score || '0%'}</td>
                <td><span class="status-pill ${item.status || 'WARNING'}">${item.status || 'WARNING'}</span></td>
                <td>${new Date(item.date || Date.now()).toLocaleDateString()}</td>
            `;
            historyTable.appendChild(row);
        });
    }

    if (searchInput) searchInput.addEventListener('input', renderHistory);
    if (statusFilter) statusFilter.addEventListener('change', renderHistory);

    renderHistory();
});
