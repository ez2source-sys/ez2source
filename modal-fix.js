/**
 * Modal Fix - Resolve hanging modal issues
 * Clean modal initialization and management
 */

class ModalManager {
    constructor() {
        this.modals = new Map();
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeModals());
        } else {
            this.initializeModals();
        }
    }

    initializeModals() {
        // Clean up any existing modal instances
        this.cleanup();
        
        // Find all modal elements
        const modalElements = document.querySelectorAll('.modal');
        
        modalElements.forEach(modalElement => {
            // Ensure modal has proper structure
            this.ensureModalStructure(modalElement);
            
            // Initialize Bootstrap modal
            try {
                const modalInstance = new bootstrap.Modal(modalElement, {
                    backdrop: true,
                    keyboard: true,
                    focus: true
                });
                
                this.modals.set(modalElement.id, modalInstance);
                
                // Add event listeners
                this.attachEventListeners(modalElement, modalInstance);
            } catch (error) {
                console.warn('Failed to initialize modal:', modalElement.id, error);
            }
        });
    }

    ensureModalStructure(modalElement) {
        // Ensure modal has proper Bootstrap classes
        if (!modalElement.classList.contains('modal')) {
            modalElement.classList.add('modal');
        }
        
        if (!modalElement.classList.contains('fade')) {
            modalElement.classList.add('fade');
        }
        
        // Ensure proper tabindex
        modalElement.setAttribute('tabindex', '-1');
        
        // Ensure modal dialog exists
        let modalDialog = modalElement.querySelector('.modal-dialog');
        if (!modalDialog) {
            modalDialog = document.createElement('div');
            modalDialog.className = 'modal-dialog';
            modalDialog.innerHTML = modalElement.innerHTML;
            modalElement.innerHTML = '';
            modalElement.appendChild(modalDialog);
        }
    }

    attachEventListeners(modalElement, modalInstance) {
        // Disable touch event propagation on modal elements
        modalElement.addEventListener('touchstart', (e) => {
            e.stopPropagation();
        }, { passive: true });

        modalElement.addEventListener('touchmove', (e) => {
            e.stopPropagation();
        }, { passive: true });

        modalElement.addEventListener('touchend', (e) => {
            e.stopPropagation();
        }, { passive: true });

        // Handle close buttons
        const closeButtons = modalElement.querySelectorAll('[data-bs-dismiss="modal"]');
        closeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                modalInstance.hide();
            });
        });

        // Handle backdrop clicks
        modalElement.addEventListener('click', (e) => {
            if (e.target === modalElement) {
                e.stopPropagation();
                modalInstance.hide();
            }
        });

        // Handle escape key
        modalElement.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                e.stopPropagation();
                modalInstance.hide();
            }
        });

        // Clean up on hide
        modalElement.addEventListener('hidden.bs.modal', () => {
            // Remove any lingering backdrops
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Restore body scroll
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
            document.body.classList.remove('modal-open');
        });

        // Prevent mobile optimization interference
        const allElements = modalElement.querySelectorAll('*');
        allElements.forEach(element => {
            element.addEventListener('touchstart', (e) => {
                e.stopPropagation();
            }, { passive: true });
            
            element.addEventListener('touchend', (e) => {
                e.stopPropagation();
            }, { passive: true });
        });
    }

    show(modalId) {
        const modal = this.modals.get(modalId);
        if (modal) {
            modal.show();
        } else {
            console.warn('Modal not found:', modalId);
        }
    }

    hide(modalId) {
        const modal = this.modals.get(modalId);
        if (modal) {
            modal.hide();
        }
    }

    cleanup() {
        // Clean up existing modals
        this.modals.forEach((modal, id) => {
            try {
                modal.dispose();
            } catch (error) {
                console.warn('Error disposing modal:', id, error);
            }
        });
        this.modals.clear();

        // Remove any lingering backdrops
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());
        
        // Reset body styles
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        document.body.classList.remove('modal-open');
    }
}

// Initialize modal manager
let modalManager;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        modalManager = new ModalManager();
    });
} else {
    modalManager = new ModalManager();
}

// Global function to show modals
window.showModal = function(modalId) {
    if (modalManager) {
        modalManager.show(modalId);
    }
};

// Global function to hide modals
window.hideModal = function(modalId) {
    if (modalManager) {
        modalManager.hide(modalId);
    }
};

// Re-initialize modals when content changes
window.reinitializeModals = function() {
    if (modalManager) {
        modalManager.initializeModals();
    }
};