document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    const historyTable = document.getElementById('historyTable');
    const emptyHistory = document.getElementById('emptyHistory');

    function downloadInspection(item) {
        const reportText = item.report || [
            'LegalMetrix Inspection Report',
            '===========================',
            'Product Name: ' + (item.productName || 'N/A'),
            'Manufacturer: ' + (item.manufacturer || 'N/A'),
            'MRP: ' + (item.mrp || 'N/A'),
            'Net Quantity: ' + (item.netQuantity || 'N/A'),
            'Manufacturing Date: ' + (item.manufacturingDate || 'N/A'),
            'Best Before: ' + (item.bestBefore || 'N/A'),
            'Consumer Care: ' + (item.consumerCare || 'N/A'),
            'Country of Origin: ' + (item.countryOrigin || 'N/A'),
            'Category: ' + (item.category || 'N/A'),
            'Compliance Score: ' + (item.score || '0%'),
            'Status: ' + (item.status || 'WARNING')
        ].join('\n');

        const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = (item.productName || 'inspection-report').replace(/[^a-z0-9]+/gi, '_').toLowerCase() + '.txt';
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    function openInspectionPreview(item) {
        if (!item.image) {
            showToast('No product image available to view.');
            return;
        }

        const previewWindow = window.open('', '_blank', 'width=700,height=760');
        if (!previewWindow) {
            showToast('Popup blocked. Please allow pop-ups to view the image.');
            return;
        }

        const html = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>${(item.productName || 'Inspection').replace(/</g, '&lt;')}</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 24px; background: #f5f7fb; }
                    .card { max-width: 540px; margin: 0 auto; background: white; border-radius: 12px; padding: 20px; box-shadow: 0 4px 20px rgba(0,0,0,.08); }
                    img { width: 100%; max-height: 420px; object-fit: contain; border-radius: 12px; background: #f3f4f6; }
                    h2 { margin: 18px 0 10px; font-size: 22px; }
                    .meta { color: #4b5563; line-height: 1.7; }
                </style>
            </head>
            <body>
                <div class="card">
                    <img src="${item.image}" alt="${(item.productName || 'Inspection').replace(/"/g, '&quot;')}" />
                    <h2>${(item.productName || 'Inspection').replace(/</g, '&lt;')}</h2>
                    <div class="meta">
                        <div><strong>MRP:</strong> ${item.mrp || '-'}</div>
                        <div><strong>Category:</strong> ${item.category || '-'}</div>
                        <div><strong>Status:</strong> ${item.status || 'WARNING'}</div>
                        <div><strong>Score:</strong> ${item.score || '0%'}</div>
                    </div>
                </div>
            </body>
            </html>
        `;

        previewWindow.document.write(html);
        previewWindow.document.close();
    }

    function retakeInspection(item) {
        if (!item || !item.image) {
            showToast('This inspection does not have a saved photo to retake.');
            return;
        }

        localStorage.setItem('legalMetrixRetakeInspection', JSON.stringify(item));
        window.location.href = 'index.html';
    }

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

            const productCell = document.createElement('td');
            productCell.textContent = item.productName || 'Unknown';

            const mrpCell = document.createElement('td');
            mrpCell.textContent = item.mrp || '-';

            const manufacturingCell = document.createElement('td');
            manufacturingCell.textContent = item.manufacturingDate || '-';

            const scoreCell = document.createElement('td');
            scoreCell.textContent = item.score || '0%';

            const statusCell = document.createElement('td');
            const statusPill = document.createElement('span');
            const status = item.status || 'WARNING';
            statusPill.className = 'status-pill ' + status;
            statusPill.textContent = status;
            statusCell.appendChild(statusPill);

            const dateCell = document.createElement('td');
            dateCell.textContent = new Date(item.date || Date.now()).toLocaleDateString();

            const actionsCell = document.createElement('td');
            const actionsWrap = document.createElement('div');
            actionsWrap.className = 'history-actions';

            const viewButton = document.createElement('button');
            viewButton.type = 'button';
            viewButton.className = 'action-button view-button';
            viewButton.title = 'View inspection';
            viewButton.textContent = 'View';
            viewButton.addEventListener('click', function () {
                openInspectionPreview(item);
            });

            const downloadButton = document.createElement('button');
            downloadButton.type = 'button';
            downloadButton.className = 'action-button download-button';
            downloadButton.title = 'Download inspection';
            downloadButton.textContent = 'Download';
            downloadButton.addEventListener('click', function () {
                downloadInspection(item);
            });

            const retakeButton = document.createElement('button');
            retakeButton.type = 'button';
            retakeButton.className = 'action-button retake-button';
            retakeButton.title = 'Retake photo';
            retakeButton.textContent = 'Retake';
            retakeButton.addEventListener('click', function () {
                retakeInspection(item);
            });

            actionsWrap.appendChild(viewButton);
            actionsWrap.appendChild(downloadButton);
            actionsWrap.appendChild(retakeButton);
            actionsCell.appendChild(actionsWrap);

            row.appendChild(productCell);
            row.appendChild(mrpCell);
            row.appendChild(manufacturingCell);
            row.appendChild(scoreCell);
            row.appendChild(statusCell);
            row.appendChild(dateCell);
            row.appendChild(actionsCell);
            historyTable.appendChild(row);
        });
    }

    if (searchInput) searchInput.addEventListener('input', renderHistory);
    if (statusFilter) statusFilter.addEventListener('change', renderHistory);

    renderHistory();
});
