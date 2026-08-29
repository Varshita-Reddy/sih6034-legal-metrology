document.addEventListener('DOMContentLoaded', function () {
    const officerInput = document.getElementById('officerInput');
    const unitInput = document.getElementById('unitInput');
    const saveProfileButton = document.getElementById('saveProfileButton');
    const profileAvatar = document.getElementById('profileAvatar');
    const profileName = document.getElementById('profileName');

    const storedOfficer = localStorage.getItem('legalMetrixOfficerName') || 'Officer';
    const storedUnit = localStorage.getItem('legalMetrixAssignedUnit') || 'Food Safety Unit';

    if (officerInput) officerInput.value = storedOfficer;
    if (unitInput) unitInput.value = storedUnit;
    if (profileName) profileName.textContent = storedOfficer;
    if (profileAvatar) profileAvatar.textContent = storedOfficer.charAt(0).toUpperCase();

    if (saveProfileButton) {
        saveProfileButton.addEventListener('click', function () {
            const name = (officerInput?.value || '').trim() || 'Officer';
            const unit = (unitInput?.value || '').trim() || 'Food Safety Unit';

            localStorage.setItem('legalMetrixOfficerName', name);
            localStorage.setItem('legalMetrixAssignedUnit', unit);

            if (profileName) profileName.textContent = name;
            if (profileAvatar) profileAvatar.textContent = name.charAt(0).toUpperCase();
            showToast('Profile saved successfully.');
        });
    }
});
