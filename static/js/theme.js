document.addEventListener('DOMContentLoaded', () => {
    const colorThemeSelect = document.getElementById('color-theme');
    const darkModeToggle = document.getElementById('dark-mode-toggle');

    // Load saved theme preferences
    const savedColorTheme = localStorage.getItem('colorTheme') || 'default';
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';

    // Apply saved preferences
    document.body.classList.toggle('dark-mode', savedDarkMode);
    document.body.className = document.body.className.replace(/theme-\w+/, '');
    if (savedColorTheme !== 'default') {
        document.body.classList.add(`theme-${savedColorTheme}`);
    }
    colorThemeSelect.value = savedColorTheme;

    // Color theme change handler
    colorThemeSelect.addEventListener('change', (e) => {
        document.body.className = document.body.className.replace(/theme-\w+/, '');
        if (e.target.value !== 'default') {
            document.body.classList.add(`theme-${e.target.value}`);
        }
        localStorage.setItem('colorTheme', e.target.value);
    });

    // Dark mode toggle handler
    darkModeToggle.addEventListener('click', () => {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
    });
});
