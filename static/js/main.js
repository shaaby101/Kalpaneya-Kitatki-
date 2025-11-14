document.addEventListener('DOMContentLoaded', function() {
    // Show loading animation when clicking on links
    const links = document.querySelectorAll('a:not([target="_blank"]):not([href^="#"]):not(.no-transition)');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't intercept if it's a special key (ctrl, cmd, etc.)
            if (e.ctrlKey || e.metaKey || e.shiftKey) {
                return true;
            }
            
            const href = this.getAttribute('href');
            
            // Only handle internal links
            if (href && !href.startsWith('http') && !href.startsWith('//')) {
                e.preventDefault();
                const pageTransition = document.querySelector('.page-transition');
                if (pageTransition) {
                    pageTransition.style.display = 'flex';
                    pageTransition.classList.remove('fade-out');
                    setTimeout(() => {
                        window.location.href = href;
                    }, 100);
                }
            }
        });
    });

    // Hide loading animation when page is fully loaded
    const handlePageLoad = function() {
        const pageTransition = document.querySelector('.page-transition');
        if (pageTransition) {
            setTimeout(function() {
                pageTransition.classList.add('fade-out');
                // Remove the element after animation completes
                setTimeout(function() {
                    pageTransition.style.display = 'none';
                }, 500);
            }, 300); // Minimum show time for the loader
        }
        
        // Remove the event listener after first load
        window.removeEventListener('load', handlePageLoad);
    };

    // If page is already loaded, run immediately, otherwise wait for load event
    if (document.readyState === 'complete') {
        handlePageLoad();
    } else {
        window.addEventListener('load', handlePageLoad);
    }

    // Force light theme
    document.documentElement.style.colorScheme = 'light';
    document.documentElement.setAttribute('data-theme', 'light');
    
    // Make sure the page is visible after JS loads
    document.documentElement.style.visibility = 'visible';
});
