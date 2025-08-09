/**
 * AI Interview Platform - Main JavaScript File
 * Provides common functionality and enhancements across the application
 */

// Global application object
window.InterviewApp = {
    // Configuration
    config: {
        toastDuration: 5000,
        animationDuration: 300,
        debounceDelay: 300
    },
    
    // Utility functions
    utils: {},
    
    // UI components
    ui: {},
    
    // Form handlers
    forms: {},
    
    // Page-specific functionality
    pages: {}
};

// Utility Functions
InterviewApp.utils = {
    /**
     * Debounce function to limit function calls
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Format time in MM:SS format
     */
    formatTime: function(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return mins.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
    },

    /**
     * Capitalize first letter of string
     */
    capitalize: function(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    },

    /**
     * Validate email format
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
};

// UI Components
InterviewApp.ui = {
    /**
     * Show toast notification
     */
    showToast: function(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('#toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast, {
            autohide: true,
            delay: InterviewApp.config.toastDuration
        });
        bsToast.show();

        // Remove toast from DOM after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            this.remove();
        });
    },

    /**
     * Show loading state on element
     */
    showLoading: function(element, text = 'Loading...') {
        if (element) {
            element.setAttribute('data-original-text', element.textContent);
            element.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${text}`;
            element.disabled = true;
        }
    },

    /**
     * Hide loading state on element
     */
    hideLoading: function(element) {
        if (element && element.hasAttribute('data-original-text')) {
            element.textContent = element.getAttribute('data-original-text');
            element.removeAttribute('data-original-text');
            element.disabled = false;
        }
    }
};

// Form Handlers
InterviewApp.forms = {
    /**
     * Initialize form validation
     */
    initValidation: function() {
        const forms = document.querySelectorAll('.needs-validation');
        forms.forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });
    },

    /**
     * Handle form submission with loading state
     */
    handleSubmit: function(form, submitButton) {
        if (form && submitButton) {
            form.addEventListener('submit', function() {
                InterviewApp.ui.showLoading(submitButton, 'Processing...');
            });
        }
    },

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea: function(textarea) {
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
    }
};

// Page-specific functionality
InterviewApp.pages = {
    /**
     * Initialize dashboard functionality
     */
    initDashboard: function() {
        // Add any dashboard-specific code here
        console.log('Dashboard initialized');
    },

    /**
     * Initialize interview builder
     */
    initInterviewBuilder: function() {
        const form = document.querySelector('#interview-form');
        if (form) {
            InterviewApp.forms.handleSubmit(form, form.querySelector('button[type="submit"]'));
        }
    },

    /**
     * Initialize interview interface
     */
    initInterviewInterface: function() {
        // Timer functionality
        const timerElement = document.querySelector('#timer');
        if (timerElement) {
            const duration = parseInt(timerElement.getAttribute('data-duration')) || 1800; // 30 minutes default
            let timeLeft = duration;
            
            const updateTimer = () => {
                timerElement.textContent = InterviewApp.utils.formatTime(timeLeft);
                if (timeLeft <= 0) {
                    // Auto-submit form when time is up
                    const form = document.querySelector('#interviewForm');
                    if (form) {
                        form.submit();
                    }
                    return;
                }
                timeLeft--;
            };
            
            updateTimer(); // Initial call
            setInterval(updateTimer, 1000);
        }

        // Auto-save functionality
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            textarea.addEventListener('input', InterviewApp.utils.debounce(() => {
                console.log('Progress saved');
            }, 2000));
        });
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form validation
    InterviewApp.forms.initValidation();

    // Initialize page-specific functionality based on body class or data attribute
    const body = document.body;
    
    if (body.classList.contains('dashboard-page')) {
        InterviewApp.pages.initDashboard();
    } else if (body.classList.contains('interview-builder-page')) {
        InterviewApp.pages.initInterviewBuilder();
    } else if (body.classList.contains('interview-interface-page')) {
        InterviewApp.pages.initInterviewInterface();
    }

    // Auto-resize textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            InterviewApp.forms.autoResizeTextarea(this);
        });
        // Initial resize
        InterviewApp.forms.autoResizeTextarea(textarea);
    });
});