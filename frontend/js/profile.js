document.addEventListener('DOMContentLoaded', function () {
    const officerInput = document.getElementById('officerInput');
    const saveProfileButton = document.getElementById('saveProfileButton');
    const profileAvatar = document.getElementById('profileAvatar');
    const profileName = document.getElementById('profileName');

    const storedOfficer = localStorage.getItem('legalMetrixOfficerName') || 'Officer';
    if (officerInput) officerInput.value = storedOfficer;
    if (profileName) profileName.textContent = storedOfficer;
    if (profileAvatar) profileAvatar.textContent = storedOfficer.charAt(0).toUpperCase();

    if (saveProfileButton) {
        saveProfileButton.addEventListener('click', function () {
            const name = (officerInput?.value || '').trim() || 'Officer';
            localStorage.setItem('legalMetrixOfficerName', name);
            if (profileName) profileName.textContent = name;
            if (profileAvatar) profileAvatar.textContent = name.charAt(0).toUpperCase();
            showToast('Profile saved successfully.');
        });
    }
});
