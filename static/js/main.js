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
        return `${mins}:${secs.toString().padStart(2, '0')}`;
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
    },

    /**
     * Generate random ID
     */
    generateId: function() {
        return 'id-' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Copy text to clipboard
     */
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            try {
                document.execCommand('copy');
                document.body.removeChild(textArea);
                return Promise.resolve();
            } catch (err) {
                document.body.removeChild(textArea);
                return Promise.reject(err);
            }
        }
    }
};

// UI Components
InterviewApp.ui = {
    /**
     * Show toast notification
     */
    showToast: function(message, type = 'info', duration = null) {
        duration = duration || InterviewApp.config.toastDuration;
        
        // Create toast container if it doesn't exist
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }

        // Create toast element
        const toastId = InterviewApp.utils.generateId();
        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        // Initialize and show toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, { autohide: true, delay: duration });
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    },

    /**
     * Show confirmation dialog
     */
    confirm: function(message, title = 'Confirm Action') {
        return new Promise((resolve) => {
            const confirmed = window.confirm(`${title}\n\n${message}`);
            resolve(confirmed);
        });
    },

    /**
     * Show loading state on element
     */
    showLoading: function(element, text = 'Loading...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            element.disabled = true;
            element.dataset.originalText = element.innerHTML;
            element.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                ${text}
            `;
        }
    },

    /**
     * Hide loading state on element
     */
    hideLoading: function(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element && element.dataset.originalText) {
            element.disabled = false;
            element.innerHTML = element.dataset.originalText;
            delete element.dataset.originalText;
        }
    },

    /**
     * Animate element entrance
     */
    animateIn: function(element, animation = 'fadeInUp') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (element) {
            element.style.animationDuration = InterviewApp.config.animationDuration + 'ms';
            element.classList.add('animate__animated', `animate__${animation}`);
            
            element.addEventListener('animationend', function() {
                element.classList.remove('animate__animated', `animate__${animation}`);
            }, { once: true });
        }
    },

    /**
     * Smooth scroll to element
     */
    scrollTo: function(target, offset = 0) {
        const element = typeof target === 'string' ? document.querySelector(target) : target;
        if (element) {
            const top = element.offsetTop - offset;
            window.scrollTo({
                top: top,
                behavior: 'smooth'
            });
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
    handleSubmit: function(form, options = {}) {
        if (typeof form === 'string') {
            form = document.querySelector(form);
        }
        
        if (!form) return;
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const loadingText = options.loadingText || 'Processing...';
        
        form.addEventListener('submit', function(event) {
            if (submitBtn) {
                InterviewApp.ui.showLoading(submitBtn, loadingText);
            }
            
            // If there are validation errors, hide loading
            setTimeout(() => {
                if (form.classList.contains('was-validated') && !form.checkValidity()) {
                    if (submitBtn) {
                        InterviewApp.ui.hideLoading(submitBtn);
                    }
                }
            }, 100);
        });
    },

    /**
     * Auto-resize textarea
     */
    autoResizeTextarea: function(textarea) {
        if (typeof textarea === 'string') {
            textarea = document.querySelector(textarea);
        }
        
        if (textarea) {
            const resize = () => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            };
            
            textarea.addEventListener('input', resize);
            resize(); // Initial resize
        }
    },

    /**
     * Character counter for textarea
     */
    addCharacterCounter: function(textarea, maxLength) {
        if (typeof textarea === 'string') {
            textarea = document.querySelector(textarea);
        }
        
        if (textarea && maxLength) {
            textarea.setAttribute('maxlength', maxLength);
            
            const counter = document.createElement('small');
            counter.className = 'form-text text-muted';
            counter.innerHTML = `<span class="char-count">0</span>/${maxLength} characters`;
            
            textarea.parentNode.appendChild(counter);
            
            const updateCounter = () => {
                const count = textarea.value.length;
                const countSpan = counter.querySelector('.char-count');
                countSpan.textContent = count;
                
                if (count > maxLength * 0.9) {
                    counter.className = 'form-text text-warning';
                } else if (count === maxLength) {
                    counter.className = 'form-text text-danger';
                } else {
                    counter.className = 'form-text text-muted';
                }
            };
            
            textarea.addEventListener('input', updateCounter);
            updateCounter();
        }
    }
};

// Page-specific functionality
InterviewApp.pages = {
    /**
     * Initialize dashboard functionality
     */
    initDashboard: function() {
        // Add click handlers for interview cards
        const interviewCards = document.querySelectorAll('[data-interview-id]');
        interviewCards.forEach(card => {
            card.style.cursor = 'pointer';
            card.addEventListener('click', function(e) {
                if (!e.target.closest('.btn')) {
                    const interviewId = this.dataset.interviewId;
                    if (interviewId) {
                        window.location.href = `/interview/${interviewId}`;
                    }
                }
            });
        });

        // Animate statistics cards
        const statCards = document.querySelectorAll('.card[class*="bg-"][class*="bg-opacity-"]');
        statCards.forEach((card, index) => {
            setTimeout(() => {
                InterviewApp.ui.animateIn(card, 'fadeInUp');
            }, index * 100);
        });
    },

    /**
     * Initialize interview builder
     */
    initInterviewBuilder: function() {
        const jobDescTextarea = document.querySelector('#job_description');
        if (jobDescTextarea) {
            InterviewApp.forms.autoResizeTextarea(jobDescTextarea);
            InterviewApp.forms.addCharacterCounter(jobDescTextarea, 5000);
        }

        // Add preview functionality
        const form = document.querySelector('#interview-form');
        if (form) {
            InterviewApp.forms.handleSubmit(form, {
                loadingText: 'Generating Questions...'
            });
        }
    },

    /**
     * Initialize interview interface
     */
    initInterviewInterface: function() {
        // Auto-save functionality
        const form = document.querySelector('#interviewForm');
        if (form) {
            const autoSave = InterviewApp.utils.debounce(() => {
                InterviewApp.pages.saveInterviewProgress();
            }, InterviewApp.config.debounceDelay);

            form.addEventListener('input', autoSave);
            form.addEventListener('change', autoSave);
        }

        // Warning before page unload
        let hasUnsavedChanges = false;
        document.addEventListener('input', () => {
            hasUnsavedChanges = true;
        });

        window.addEventListener('beforeunload', (e) => {
            if (hasUnsavedChanges) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Mark changes as saved when form is submitted
        if (form) {
            form.addEventListener('submit', () => {
                hasUnsavedChanges = false;
            });
        }
    },

    /**
     * Save interview progress (placeholder for future localStorage implementation)
     */
    saveInterviewProgress: function() {
        // This could save form data to localStorage for recovery
        console.log('Interview progress saved');
    },

    /**
     * Initialize analytics page
     */
    initAnalytics: function() {
        // Add export functionality
        const exportBtn = document.querySelector('#exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function() {
                InterviewApp.ui.showLoading(this, 'Exporting...');
                
                // Simulate export delay
                setTimeout(() => {
                    InterviewApp.ui.hideLoading(this);
                    InterviewApp.ui.showToast('Data exported successfully', 'success');
                }, 2000);
            });
        }

        // Animate chart containers when they come into view
        const chartContainers = document.querySelectorAll('canvas');
        if (window.IntersectionObserver) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        InterviewApp.ui.animateIn(entry.target.closest('.card'), 'fadeInUp');
                        observer.unobserve(entry.target);
                    }
                });
            });

            chartContainers.forEach(canvas => {
                observer.observe(canvas);
            });
        }
    }
};

// Global event handlers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Initialize form validation
    InterviewApp.forms.initValidation();

    // Initialize auto-resize for all textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        InterviewApp.forms.autoResizeTextarea(textarea);
    });

    // Add click-to-copy functionality for elements with data-copy attribute
    document.querySelectorAll('[data-copy]').forEach(element => {
        element.style.cursor = 'pointer';
        element.title = 'Click to copy';
        
        element.addEventListener('click', function() {
            const textToCopy = this.dataset.copy || this.textContent;
            InterviewApp.utils.copyToClipboard(textToCopy)
                .then(() => {
                    InterviewApp.ui.showToast('Copied to clipboard!', 'success', 2000);
                })
                .catch(() => {
                    InterviewApp.ui.showToast('Failed to copy', 'danger', 2000);
                });
        });
    });

    // Add confirmation dialogs for dangerous actions
    document.querySelectorAll('[data-confirm]').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const message = this.dataset.confirm;
            
            InterviewApp.ui.confirm(message)
                .then(confirmed => {
                    if (confirmed) {
                        // If it's a link, navigate to it
                        if (this.href) {
                            window.location.href = this.href;
                        }
                        // If it's a form submit button, submit the form
                        else if (this.type === 'submit') {
                            this.closest('form').submit();
                        }
                    }
                });
        });
    });

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Page-specific initialization based on body class or data attributes
    const body = document.body;
    
    if (body.classList.contains('dashboard-page') || window.location.pathname.includes('/dashboard')) {
        InterviewApp.pages.initDashboard();
    }
    
    if (body.classList.contains('interview-builder-page') || window.location.pathname.includes('/interview/create')) {
        InterviewApp.pages.initInterviewBuilder();
    }
    
    if (body.classList.contains('interview-interface-page') || window.location.pathname.includes('/interview/') && !window.location.pathname.includes('/create')) {
        InterviewApp.pages.initInterviewInterface();
    }
    
    if (body.classList.contains('analytics-page') || window.location.pathname.includes('/candidates/')) {
        InterviewApp.pages.initAnalytics();
    }

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                InterviewApp.ui.scrollTo(target, 80);
            }
        });
    });

    // Add loading animation to page transitions
    document.querySelectorAll('a[href]:not([href^="#"]):not([target="_blank"])').forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't add loading for certain actions
            if (this.dataset.noLoading || this.closest('.dropdown') || this.classList.contains('dropdown-item')) {
                return;
            }
            
            const body = document.body;
            body.style.opacity = '0.8';
            body.style.transition = 'opacity 0.3s ease';
            
            // Reset opacity if navigation is cancelled
            setTimeout(() => {
                body.style.opacity = '1';
            }, 1000);
        });
    });
});

// Handle page visibility changes (pause timers, etc.)
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden - pause any timers or animations
        console.log('Page hidden - pausing activity');
    } else {
        // Page is visible - resume activity
        console.log('Page visible - resuming activity');
    }
});

// Error handling for uncaught errors
window.addEventListener('error', function(event) {
    console.error('Global error:', event.error);
    InterviewApp.ui.showToast('An unexpected error occurred. Please refresh the page.', 'danger');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    InterviewApp.ui.showToast('An error occurred while processing your request.', 'warning');
});

// Export for global access
window.InterviewApp = InterviewApp;
