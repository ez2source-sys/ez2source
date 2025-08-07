/**
 * Emergency Modal Fix - Direct modal handling to fix hanging issue
 * This provides a fallback solution for modal interaction problems
 */

// Force modal to work properly
document.addEventListener('DOMContentLoaded', function() {
    // Wait for page to fully load
    setTimeout(() => {
        // Force remove any hanging backdrops
        const existingBackdrops = document.querySelectorAll('.modal-backdrop');
        existingBackdrops.forEach(backdrop => backdrop.remove());
        
        // Reset body classes
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
        
        // Find all modal triggers and add direct click handlers
        const modalTriggers = document.querySelectorAll('[data-bs-toggle="modal"]');
        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const targetModal = document.querySelector(this.getAttribute('data-bs-target'));
                if (targetModal) {
                    // Force show the modal
                    targetModal.style.display = 'block';
                    targetModal.style.zIndex = '10000';
                    targetModal.classList.add('show');
                    
                    // Add backdrop
                    const backdrop = document.createElement('div');
                    backdrop.className = 'modal-backdrop fade show';
                    backdrop.style.zIndex = '9999';
                    document.body.appendChild(backdrop);
                    
                    // Add modal-open class to body
                    document.body.classList.add('modal-open');
                    
                    // Handle close buttons
                    const closeButtons = targetModal.querySelectorAll('[data-bs-dismiss="modal"], .btn-close');
                    closeButtons.forEach(closeBtn => {
                        closeBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            e.stopPropagation();
                            closeModal(targetModal);
                        });
                    });
                    
                    // Handle backdrop click to close
                    backdrop.addEventListener('click', function(e) {
                        if (e.target === backdrop) {
                            closeModal(targetModal);
                        }
                    });
                    
                    // Handle escape key
                    document.addEventListener('keydown', function(e) {
                        if (e.key === 'Escape' && targetModal.classList.contains('show')) {
                            closeModal(targetModal);
                        }
                    });
                }
            });
        });
        
        function closeModal(modal) {
            // Hide modal
            modal.style.display = 'none';
            modal.classList.remove('show');
            
            // Remove backdrop
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) {
                backdrop.remove();
            }
            
            // Reset body
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }
        
        // Force all modal elements to be interactive
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.pointerEvents = 'auto';
            
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent) {
                modalContent.style.pointerEvents = 'auto';
                modalContent.style.zIndex = '10001';
            }
            
            const modalDialog = modal.querySelector('.modal-dialog');
            if (modalDialog) {
                modalDialog.style.pointerEvents = 'auto';
                modalDialog.style.zIndex = '10002';
            }
            
            // Force all elements inside modal to be interactive
            const allElements = modal.querySelectorAll('*');
            allElements.forEach(element => {
                element.style.pointerEvents = 'auto';
            });
        });
        
    }, 100);
});