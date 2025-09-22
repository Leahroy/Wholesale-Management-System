// Highlight the current sidebar link
document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll('.sidebar ul li a');

    links.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.style.backgroundColor = '#1abc9c'; // highlight current page
        }
    });
});