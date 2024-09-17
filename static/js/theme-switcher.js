document.addEventListener('DOMContentLoaded', () => {
    const switcher = document.createElement('div');
    switcher.className = 'theme-switcher';
    switcher.innerText = 'Switch Theme';
    document.body.appendChild(switcher);

    const savedTheme = localStorage.getItem('theme') || 'dark-theme';
    if (savedTheme === 'light-theme') {
        document.body.classList.add('light-theme');
    }

    switcher.addEventListener('click', () => {
        if (document.body.classList.contains('light-theme')) {
            document.body.classList.remove('light-theme');
            localStorage.setItem('theme', 'dark-theme');
        } else {
            document.body.classList.add('light-theme');
            localStorage.setItem('theme', 'light-theme');
        }
    });
});

