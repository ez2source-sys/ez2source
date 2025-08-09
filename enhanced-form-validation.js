/**
 * Enhanced Form Validation with User-Friendly Experience
 * Clears validation errors when users start typing
 * Provides real-time feedback without blocking form interaction
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('candidateRegistrationForm');
    if (!form) return;

    // Enhanced validation patterns
    const validationRules = {
        first_name: {
            pattern: /^[A-Za-z\s]{2,50}$/,
            message: 'Please enter a valid first name (letters only, 2-50 characters)'
        },
        last_name: {
            pattern: /^[A-Za-z\s]{2,50}$/,
            message: 'Please enter a valid last name (letters only, 2-50 characters)'
        },
        email: {
            pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Please enter a valid email address'
        },
        phone: {
            pattern: /^[\d\s\-\+\(\)]{10,15}$/,
            message: 'Please enter a valid phone number'
        },
        job_title: {
            pattern: /^.{2,100}$/,
            message: 'Job title must be 2-100 characters'
        }
    };

    // Clear validation errors on input
    function clearValidationError(field) {
        const fieldElement = document.getElementById(field);
        if (!fieldElement) return;

        // Remove Bootstrap validation classes
        fieldElement.classList.remove('is-invalid');
        fieldElement.classList.remove('is-valid');
        
        // Remove error styling
        fieldElement.style.borderColor = '';
        fieldElement.style.backgroundColor = '';
        
        // Hide error message
        const errorElement = fieldElement.parentNode.querySelector('.invalid-feedback') || 
                           fieldElement.parentNode.parentNode.querySelector('.invalid-feedback');
        if (errorElement) {
            errorElement.style.display = 'none';
        }

        // Hide field-specific error in main alert
        const mainAlert = document.querySelector('.alert-danger');
        if (mainAlert) {
            mainAlert.style.display = 'none';
        }
    }

    // Show validation success
    function showValidationSuccess(field) {
        const fieldElement = document.getElementById(field);
        if (!fieldElement) return;

        fieldElement.classList.remove('is-invalid');
        fieldElement.classList.add('is-valid');
        fieldElement.style.borderColor = '#28a745';
        fieldElement.style.backgroundColor = '#f8fff9';
    }

    // Show validation error
    function showValidationError(field, message) {
        const fieldElement = document.getElementById(field);
        if (!fieldElement) return;

        fieldElement.classList.remove('is-valid');
        fieldElement.classList.add('is-invalid');
        fieldElement.style.borderColor = '#dc3545';
        fieldElement.style.backgroundColor = '#fff5f5';

        // Show or create error message
        let errorElement = fieldElement.parentNode.querySelector('.invalid-feedback') || 
                          fieldElement.parentNode.parentNode.querySelector('.invalid-feedback');
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'invalid-feedback';
            fieldElement.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }

    // Real-time validation on input
    function validateField(field, value) {
        const rule = validationRules[field];
        if (!rule) return true;

        if (value.trim() === '') {
            clearValidationError(field);
            return true; // Don't show error for empty fields until submit
        }

        if (rule.pattern.test(value)) {
            showValidationSuccess(field);
            return true;
        } else {
            showValidationError(field, rule.message);
            return false;
        }
    }

    // Add event listeners for real-time validation
    Object.keys(validationRules).forEach(field => {
        const fieldElement = document.getElementById(field);
        if (!fieldElement) return;

        // Clear errors when user starts typing
        fieldElement.addEventListener('input', function() {
            clearValidationError(field);
            
            // Validate after a short delay to avoid too frequent validation
            clearTimeout(fieldElement.validationTimeout);
            fieldElement.validationTimeout = setTimeout(() => {
                validateField(field, this.value);
            }, 500);
        });

        // Clear errors immediately on focus
        fieldElement.addEventListener('focus', function() {
            clearValidationError(field);
        });

        // Validate on blur
        fieldElement.addEventListener('blur', function() {
            if (this.value.trim() !== '') {
                validateField(field, this.value);
            }
        });
    });

    // Handle form submission
    form.addEventListener('submit', function(e) {
        let isValid = true;

        // Validate all fields
        Object.keys(validationRules).forEach(field => {
            const fieldElement = document.getElementById(field);
            if (!fieldElement) return;

            const value = fieldElement.value.trim();
            
            // Check required fields
            if (fieldElement.hasAttribute('required') && value === '') {
                showValidationError(field, `${field.replace('_', ' ')} is required`);
                isValid = false;
                return;
            }

            // Validate pattern
            if (value !== '' && !validateField(field, value)) {
                isValid = false;
            }
        });

        // Prevent submission if invalid
        if (!isValid) {
            e.preventDefault();
            
            // Show general error message
            let generalError = document.querySelector('.validation-summary');
            if (!generalError) {
                generalError = document.createElement('div');
                generalError.className = 'alert alert-danger validation-summary';
                generalError.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Please correct the errors above before submitting.';
                form.insertBefore(generalError, form.firstChild);
            }
            generalError.style.display = 'block';

            // Scroll to first error
            const firstError = form.querySelector('.is-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
        }
    });

    // Initialize: Clear any existing validation errors on page load
    setTimeout(() => {
        Object.keys(validationRules).forEach(field => {
            clearValidationError(field);
        });
    }, 100);
});
