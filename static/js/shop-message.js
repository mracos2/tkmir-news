// Shop Message Functionality
document.addEventListener('DOMContentLoaded', function() {
    const shopLinks = document.querySelectorAll('.shop-link');
    const shopMessage = document.getElementById('shopMessage');
    const overlay = document.getElementById('overlay');
    const closeMessage = document.getElementById('closeMessage');
    const mobileMenu = document.getElementById('mobileMenu');

    function showShopMessage() {
        shopMessage.style.display = 'block';
        overlay.style.display = 'block';
        overlay.style.opacity = '0.5';
        
        // Hide mobile menu if it's open
        if (mobileMenu.style.display === 'block') {
            mobileMenu.style.transform = 'translateX(100%)';
            mobileMenu.style.display = 'none';
        }
    }

    function hideShopMessage() {
        shopMessage.style.display = 'none';
        overlay.style.display = 'none';
        overlay.style.opacity = '0';
    }

    // Add event listeners to all shop links
    shopLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            showShopMessage();
        });
    });

    // Close message when clicking OK or overlay
    if (closeMessage) {
        closeMessage.addEventListener('click', hideShopMessage);
    }
    
    if (overlay) {
        overlay.addEventListener('click', hideShopMessage);
    }
});