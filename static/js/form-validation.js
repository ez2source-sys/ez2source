/**
 * Comprehensive Form Validation System
 * Provides client-side validation with red borders, light gray placeholders, and descriptive error messages
 */

class FormValidator {
    constructor() {
        this.validators = {
            email: {
                pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                message: 'Please enter a valid email address'
            },
            phone: {
                pattern: /^[\+]?[1-9][\d]{0,15}$/,
                message: 'Please enter a valid phone number'
            },
            password: {
                pattern: /^.{8,}$/,
                message: 'Password must be at least 8 characters long'
            },
            url: {
                pattern: /^https?:\/\/[^\s$.?#].[^\s]*$/,
                message: 'Please enter a valid URL'
            },
            text: {
                pattern: /^.+$/,
                message: 'This field is required'
            },
            number: {
                pattern: /^\d+$/,
                message: 'Please enter a valid number'
            }
        };
        
        this.init();
    }
    
    init() {
        // Add validation to all forms on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.attachValidationToForms();
        });
    }
    
    attachValidationToForms() {
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            // Add real-time validation
            form.addEventListener('input', (e) => this.validateField(e.target));
            form.addEventListener('blur', (e) => this.validateField(e.target));
            
            // Add form submission validation
            form.addEventListener('submit', (e) => this.validateForm(e));
        });
    }
    
    validateField(field) {
        if (!field.hasAttribute('data-validate')) return true;
        
        const validationType = field.getAttribute('data-validate');
        const isRequired = field.hasAttribute('required') || field.hasAttribute('data-required');
        const value = field.value.trim();
        
        // Clear previous error state
        this.clearFieldError(field);
        
        // Check if field is required and empty
        if (isRequired && !value) {
            this.showFieldError(field, this.getRequiredMessage(field));
            return false;
        }
        
        // Skip validation if field is empty and not required
        if (!value && !isRequired) {
            return true;
        }
        
        // Validate field value
        const validator = this.validators[validationType];
        if (validator && !validator.pattern.test(value)) {
            this.showFieldError(field, validator.message);
            return false;
        }
        
        // Custom validation for specific fields
        if (validationType === 'password_confirm') {
            const passwordField = document.querySelector('[name="password"]');
            if (passwordField && value !== passwordField.value) {
                this.showFieldError(field, 'Passwords do not match');
                return false;
            }
        }
        
        return true;
    }
    
    validateForm(event) {
        const form = event.target;
        const fields = form.querySelectorAll('[data-validate]');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        if (!isValid) {
            event.preventDefault();
            
            // Focus on first invalid field
            const firstInvalidField = form.querySelector('.form-field-error');
            if (firstInvalidField) {
                firstInvalidField.focus();
            }
            
            // Show general error message
            this.showFormError(form, 'Please correct the errors below and try again.');
        }
        
        return isValid;
    }
    
    showFieldError(field, message) {
        // Add error class to field
        field.classList.add('form-field-error');
        
        // Create or update error message
        let errorElement = field.parentNode.querySelector('.form-error-message');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'form-error-message';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
    
    clearFieldError(field) {
        field.classList.remove('form-field-error');
        
        const errorElement = field.parentNode.querySelector('.form-error-message');
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }
    
    showFormError(form, message) {
        let errorContainer = form.querySelector('.form-general-error');
        if (!errorContainer) {
            errorContainer = document.createElement('div');
            errorContainer.className = 'form-general-error alert alert-danger';
            form.insertBefore(errorContainer, form.firstChild);
        }
        
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
    }
    
    getRequiredMessage(field) {
        const fieldName = field.getAttribute('data-field-name') || 
                         field.getAttribute('name') || 
                         field.getAttribute('placeholder') || 
                         'This field';
        
        return `${fieldName} is required`;
    }
}

// Initialize form validation
const formValidator = new FormValidator();

// Export for use in other scripts
window.FormValidator = FormValidator;