/**
 * Mobile Optimizations for Job2Hire
 * Enhanced touch interactions, performance improvements, and responsive behaviors
 */

class MobileOptimizer {
    constructor() {
        this.isMobile = window.innerWidth < 768;
        this.isTablet = window.innerWidth >= 768 && window.innerWidth < 992;
        this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        this.sidebar = document.getElementById('sidebar');
        this.mobileOverlay = document.getElementById('mobile-overlay');
        this.mainContent = document.getElementById('mainContent');
        
        this.init();
    }

    init() {
        this.setupTouchOptimizations();
        this.setupSidebarBehavior();
        this.setupFormOptimizations();
        this.setupPerformanceOptimizations();
        this.setupLoadingOptimizations();
        this.setupResizeHandler();
        this.setupGestureHandling();
    }

    setupTouchOptimizations() {
        // Improve touch responsiveness
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });

        // Add touch feedback to interactive elements (excluding modal elements)
        const interactiveElements = document.querySelectorAll('.btn, .sidebar-item, .nav-link, .dropdown-item, .card-header[data-bs-toggle]');
        interactiveElements.forEach(element => {
            // Skip modal elements to prevent interference
            if (element.closest('.modal') || element.closest('[data-bs-toggle="modal"]')) {
                return;
            }
            
            element.addEventListener('touchstart', this.addTouchFeedback.bind(this), { passive: true });
            element.addEventListener('touchend', this.removeTouchFeedback.bind(this), { passive: true });
            element.addEventListener('touchcancel', this.removeTouchFeedback.bind(this), { passive: true });
        });

        // Prevent double-tap zoom on buttons (excluding modal buttons)
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            // Skip modal buttons to prevent interference
            if (button.closest('.modal') || button.hasAttribute('data-bs-toggle')) {
                return;
            }
            
            button.addEventListener('touchend', (e) => {
                e.preventDefault();
                e.target.click();
            });
        });
    }

    setupSidebarBehavior() {
        if (!this.isMobile) return;

        const mobileToggle = document.getElementById('mobile-nav-toggle');
        const sidebarOverlay = document.getElementById('sidebarOverlay');

        // Mobile sidebar toggle
        if (mobileToggle) {
            mobileToggle.addEventListener('click', this.toggleMobileSidebar.bind(this));
        }

        // Close sidebar when clicking overlay
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', this.closeMobileSidebar.bind(this));
        }

        // Close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            if (this.sidebar && this.sidebar.classList.contains('show')) {
                if (!this.sidebar.contains(e.target) && !mobileToggle?.contains(e.target)) {
                    this.closeMobileSidebar();
                }
            }
        });

        // Handle sidebar navigation
        const sidebarItems = document.querySelectorAll('.sidebar-item');
        sidebarItems.forEach(item => {
            item.addEventListener('click', () => {
                if (this.isMobile) {
                    this.closeMobileSidebar();
                }
            });
        });
    }

    setupFormOptimizations() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            // Prevent zoom on iOS when focusing inputs
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.type !== 'file') {
                    input.style.fontSize = '16px';
                }
            });

            // Optimize form submission
            form.addEventListener('submit', this.optimizeFormSubmission.bind(this));
        });

        // Enhance autocomplete behavior
        const autocompleteInputs = document.querySelectorAll('[data-autocomplete]');
        autocompleteInputs.forEach(input => {
            this.enhanceAutocomplete(input);
        });
    }

    setupPerformanceOptimizations() {
        // Lazy load images
        if ('IntersectionObserver' in window) {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });
            images.forEach(img => imageObserver.observe(img));
        }

        // Optimize scroll performance
        let isScrolling = false;
        window.addEventListener('scroll', () => {
            if (!isScrolling) {
                window.requestAnimationFrame(() => {
                    this.handleScroll();
                    isScrolling = false;
                });
                isScrolling = true;
            }
        }, { passive: true });

        // Preload critical resources
        this.preloadCriticalResources();
    }

    setupLoadingOptimizations() {
        // Show skeleton loading for dynamic content
        const loadingContainers = document.querySelectorAll('[data-loading]');
        loadingContainers.forEach(container => {
            this.showSkeletonLoader(container);
        });

        // Optimize AJAX requests
        this.setupAjaxOptimizations();

        // Implement service worker for caching (if supported)
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }
    }

    setupResizeHandler() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleResize();
            }, 100);
        });
    }

    setupGestureHandling() {
        if (!this.isTouch) return;

        // Swipe to open/close sidebar
        let startX, startY, currentX, currentY;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!startX || !startY) return;
            currentX = e.touches[0].clientX;
            currentY = e.touches[0].clientY;
        }, { passive: true });

        document.addEventListener('touchend', () => {
            if (!startX || !startY || !currentX || !currentY) return;

            const diffX = currentX - startX;
            const diffY = currentY - startY;

            // Only handle horizontal swipes
            if (Math.abs(diffX) > Math.abs(diffY)) {
                if (diffX > 50 && startX < 50) {
                    // Swipe right from left edge - open sidebar
                    this.openMobileSidebar();
                } else if (diffX < -50 && this.sidebar?.classList.contains('show')) {
                    // Swipe left - close sidebar
                    this.closeMobileSidebar();
                }
            }

            startX = startY = currentX = currentY = null;
        }, { passive: true });
    }

    // Touch feedback methods
    addTouchFeedback(e) {
        e.target.style.transform = 'scale(0.98)';
        e.target.style.opacity = '0.8';
    }

    removeTouchFeedback(e) {
        e.target.style.transform = '';
        e.target.style.opacity = '';
    }

    // Sidebar methods
    toggleMobileSidebar() {
        if (this.sidebar?.classList.contains('show')) {
            this.closeMobileSidebar();
        } else {
            this.openMobileSidebar();
        }
    }

    openMobileSidebar() {
        if (!this.sidebar) return;
        this.sidebar.classList.add('show');
        if (this.mobileOverlay) {
            this.mobileOverlay.classList.add('show');
        }
        document.body.style.overflow = 'hidden';
    }

    closeMobileSidebar() {
        if (!this.sidebar) return;
        this.sidebar.classList.remove('show');
        if (this.mobileOverlay) {
            this.mobileOverlay.classList.remove('show');
        }
        document.body.style.overflow = '';
    }

    // Form optimization methods
    optimizeFormSubmission(e) {
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
            
            // Re-enable after 5 seconds to prevent permanent disability
            setTimeout(() => {
                submitBtn.disabled = false;
                submitBtn.innerHTML = submitBtn.dataset.originalText || 'Submit';
            }, 5000);
        }
    }

    enhanceAutocomplete(input) {
        let timeout;
        input.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                // Trigger autocomplete search
                this.triggerAutocomplete(input);
            }, 300);
        });
    }

    triggerAutocomplete(input) {
        // Implementation depends on specific autocomplete needs
        const event = new CustomEvent('autocomplete-search', {
            detail: { value: input.value }
        });
        input.dispatchEvent(event);
    }

    // Performance methods
    handleScroll() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Update scroll-dependent elements
        this.updateScrollElements(scrollTop);
    }

    updateScrollElements(scrollTop) {
        // Add scroll-based optimizations here
        const header = document.querySelector('.navbar');
        if (header) {
            if (scrollTop > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }
    }

    preloadCriticalResources() {
        // Preload fonts
        const fontUrls = [
            'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
        ];
        
        fontUrls.forEach(url => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = url;
            link.as = 'style';
            document.head.appendChild(link);
        });
    }

    showSkeletonLoader(container) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton skeleton-card';
        container.appendChild(skeleton);
        
        // Remove skeleton after content loads
        setTimeout(() => {
            skeleton.remove();
        }, 1000);
    }

    setupAjaxOptimizations() {
        // Override fetch to add loading states
        const originalFetch = window.fetch;
        window.fetch = async function(...args) {
            const loadingIndicator = document.querySelector('.loading-indicator');
            if (loadingIndicator) {
                loadingIndicator.style.display = 'block';
            }
            
            try {
                const response = await originalFetch.apply(this, args);
                return response;
            } finally {
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            }
        };
    }

    registerServiceWorker() {
        navigator.serviceWorker.register('/static/sw.js').then(registration => {
            console.log('Service Worker registered:', registration);
        }).catch(error => {
            console.log('Service Worker registration failed:', error);
        });
    }

    handleResize() {
        const newWidth = window.innerWidth;
        const wasMobile = this.isMobile;
        
        this.isMobile = newWidth < 768;
        this.isTablet = newWidth >= 768 && newWidth < 992;
        
        // Handle mobile to desktop transition
        if (wasMobile && !this.isMobile) {
            this.closeMobileSidebar();
        }
        
        // Update viewport height for mobile browsers
        if (this.isMobile) {
            document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
        }
    }

    // Touch event handlers
    handleTouchStart(e) {
        // Add any touch start logic here
    }

    handleTouchMove(e) {
        // Prevent scrolling when sidebar is open
        if (this.sidebar?.classList.contains('show')) {
            e.preventDefault();
        }
    }

    handleTouchEnd(e) {
        // Add any touch end logic here
    }
}

// Initialize mobile optimizations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new MobileOptimizer();
});

// Export for use in other scripts
window.MobileOptimizer = MobileOptimizer;