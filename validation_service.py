"""
Enhanced Validation Service for Job2Hire
Provides comprehensive validation for authentication and user input
"""
import re
import logging
from typing import Dict, List, Tuple, Optional
from flask import request
from datetime import datetime, timedelta

class ValidationService:
    """Comprehensive validation service for authentication and forms"""
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$')
    
    # Email validation
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # Username validation
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{3,30}$')
    
    # Phone validation
    PHONE_PATTERN = re.compile(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$')
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, str]:
        """Validate email format and requirements"""
        if not email:
            return False, "Email is required"
        
        if len(email) > 120:
            return False, "Email must be less than 120 characters"
        
        if not ValidationService.EMAIL_PATTERN.match(email):
            return False, "Please enter a valid email address"
        
        # Check for common disposable email domains
        disposable_domains = [
            '10minutemail.com', 'guerrillamail.com', 'tempmail.org',
            'throwaway.email', 'temp-mail.org', 'mailinator.com'
        ]
        
        email_domain = email.split('@')[1].lower()
        if email_domain in disposable_domains:
            return False, "Disposable email addresses are not allowed"
        
        return True, ""

    @staticmethod
    def validate_email_uniqueness(email: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check if email is unique across the platform"""
        from app import db
        from models import User
        
        # Basic email validation first
        is_valid, error_msg = ValidationService.validate_email(email)
        if not is_valid:
            return is_valid, error_msg
        
        # Check for existing email
        query = User.query.filter_by(email=email.lower())
        if user_id:
            query = query.filter(User.id != user_id)
        
        existing_user = query.first()
        if existing_user:
            return False, "This email address is already registered. Please use a different email."
        
        return True, ""

    @staticmethod
    def validate_phone_uniqueness(phone: str, user_id: Optional[int] = None) -> Tuple[bool, str]:
        """Check if phone number is unique across the platform"""
        from app import db
        from models import User
        
        if not phone:
            return True, ""  # Phone is optional
        
        # Basic phone validation first
        is_valid, error_msg = ValidationService.validate_phone(phone)
        if not is_valid:
            return is_valid, error_msg
        
        # Normalize phone number for comparison
        normalized_phone = ValidationService.normalize_phone(phone)
        
        # Check for existing phone
        query = User.query.filter_by(phone=normalized_phone)
        if user_id:
            query = query.filter(User.id != user_id)
        
        existing_user = query.first()
        if existing_user:
            return False, "This phone number is already registered. Please use a different phone number."
        
        return True, ""

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number for storage and comparison"""
        if not phone:
            return ""
        
        # Remove all non-digit characters except +
        normalized = re.sub(r'[^\d+]', '', phone)
        
        # If it starts with +1, keep it
        if normalized.startswith('+1'):
            return normalized
        
        # If it's 11 digits starting with 1, add +
        if len(normalized) == 11 and normalized.startswith('1'):
            return '+' + normalized
        
        # If it's 10 digits, add +1
        if len(normalized) == 10:
            return '+1' + normalized
        
        return normalized
    
    @staticmethod
    def validate_password(password: str, username: str = None) -> Tuple[bool, List[str]]:
        """Validate password strength and requirements"""
        errors = []
        
        if not password:
            errors.append("Password is required")
            return False, errors
        
        if len(password) < ValidationService.MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {ValidationService.MIN_PASSWORD_LENGTH} characters long")
        
        if len(password) > ValidationService.MAX_PASSWORD_LENGTH:
            errors.append(f"Password must be less than {ValidationService.MAX_PASSWORD_LENGTH} characters long")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[@$!%*?&]', password):
            errors.append("Password must contain at least one special character (@$!%*?&)")
        
        # Check for common weak passwords
        weak_passwords = [
            'password', '12345678', 'qwerty123', 'abc123456',
            'password123', 'admin123', 'letmein123'
        ]
        
        if password.lower() in weak_passwords:
            errors.append("Password is too common, please choose a stronger password")
        
        # Check if password contains username
        if username and username.lower() in password.lower():
            errors.append("Password cannot contain your username")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """Validate username format and requirements"""
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 30:
            return False, "Username must be less than 30 characters long"
        
        if not ValidationService.USERNAME_PATTERN.match(username):
            return False, "Username can only contain letters, numbers, and underscores"
        
        # Check for reserved usernames
        reserved_usernames = [
            'admin', 'administrator', 'root', 'system', 'api', 'www',
            'mail', 'email', 'support', 'help', 'info', 'contact',
            'talentiq', 'talent', 'recruiter', 'candidate'
        ]
        
        if username.lower() in reserved_usernames:
            return False, "This username is reserved, please choose another"
        
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate phone number format"""
        if not phone:
            return True, ""  # Phone is optional
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) < 10:
            return False, "Phone number must be at least 10 digits"
        
        if len(digits_only) > 15:
            return False, "Phone number is too long"
        
        if not ValidationService.PHONE_PATTERN.match(phone):
            return False, "Please enter a valid phone number (e.g., +1-555-123-4567)"
        
        return True, ""
    
    @staticmethod
    def validate_name(name: str, field_name: str) -> Tuple[bool, str]:
        """Validate first and last names"""
        if not name:
            return False, f"{field_name} is required"
        
        if len(name) < 2:
            return False, f"{field_name} must be at least 2 characters long"
        
        if len(name) > 50:
            return False, f"{field_name} must be less than 50 characters long"
        
        if not re.match(r'^[a-zA-Z\s\'-]+$', name):
            return False, f"{field_name} can only contain letters, spaces, hyphens, and apostrophes"
        
        return True, ""
    
    @staticmethod
    def validate_role(role: str) -> Tuple[bool, str]:
        """Validate user role selection"""
        valid_roles = ['recruiter', 'candidate', 'admin', 'viewer']
        
        if not role:
            return False, "Role selection is required"
        
        if role not in valid_roles:
            return False, "Invalid role selected"
        
        return True, ""
    
    @staticmethod
    def validate_organization_data(org_name: str, org_type: str = None) -> Tuple[bool, List[str]]:
        """Validate organization information"""
        errors = []
        
        if not org_name:
            errors.append("Organization name is required")
        elif len(org_name) < 2:
            errors.append("Organization name must be at least 2 characters long")
        elif len(org_name) > 100:
            errors.append("Organization name must be less than 100 characters long")
        
        if org_type and org_type not in ['startup', 'small_business', 'enterprise', 'non_profit', 'government']:
            errors.append("Invalid organization type")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_profile_data(data: Dict) -> Tuple[bool, Dict[str, str]]:
        """Validate profile completion data"""
        errors = {}
        
        # Validate job title
        if 'job_title' in data and data['job_title']:
            if len(data['job_title']) > 100:
                errors['job_title'] = "Job title must be less than 100 characters"
        
        # Validate bio
        if 'bio' in data and data['bio']:
            if len(data['bio']) > 1000:
                errors['bio'] = "Bio must be less than 1000 characters"
        
        # Validate experience years
        if 'experience_years' in data and data['experience_years']:
            try:
                years = int(data['experience_years'])
                if years < 0 or years > 50:
                    errors['experience_years'] = "Experience years must be between 0 and 50"
            except ValueError:
                errors['experience_years'] = "Experience years must be a valid number"
        
        # Validate LinkedIn URL
        if 'linkedin_url' in data and data['linkedin_url']:
            linkedin_pattern = re.compile(r'^https?://(www\.)?linkedin\.com/in/[\w\-]+/?$')
            if not linkedin_pattern.match(data['linkedin_url']):
                errors['linkedin_url'] = "Please enter a valid LinkedIn profile URL"
        
        # Validate portfolio URL
        if 'portfolio_url' in data and data['portfolio_url']:
            url_pattern = re.compile(r'^https?://[\w\-]+(\.[\w\-]+)+[/#?]?.*$')
            if not url_pattern.match(data['portfolio_url']):
                errors['portfolio_url'] = "Please enter a valid portfolio URL"
        
        return len(errors) == 0, errors
    
    @staticmethod
    def check_rate_limit(ip_address: str, action: str, limit: int = 5, window_minutes: int = 15) -> Tuple[bool, str]:
        """Check rate limiting for actions like login attempts"""
        # This would typically use Redis or database for production
        # For now, return True (no rate limiting implemented)
        return True, ""
    
    @staticmethod
    def validate_csrf_token(token: str, session_token: str) -> bool:
        """Validate CSRF token (basic implementation)"""
        # In production, implement proper CSRF protection
        return True
    
    @staticmethod
    def sanitize_input(data: str, max_length: int = None) -> str:
        """Sanitize user input to prevent XSS"""
        if not data:
            return ""
        
        # Basic sanitization - remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', str(data))
        
        if max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_file_upload(file_data, allowed_extensions: List[str], max_size_mb: int = 5) -> Tuple[bool, str]:
        """Validate file uploads"""
        if not file_data:
            return False, "No file provided"
        
        # Check file extension
        filename = file_data.filename.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return False, f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        
        # Check file size (basic check)
        max_size_bytes = max_size_mb * 1024 * 1024
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning
        
        if file_size > max_size_bytes:
            return False, f"File size too large. Maximum size: {max_size_mb}MB"
        
        return True, ""

# Validation decorator for routes
def validate_form_data(validation_rules):
    """Decorator to validate form data based on rules"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                errors = {}
                
                for field, rules in validation_rules.items():
                    value = request.form.get(field, '')
                    
                    for rule in rules:
                        is_valid, error_msg = rule(value)
                        if not is_valid:
                            errors[field] = error_msg
                            break
                
                if errors:
                    # Add validation errors to template context
                    kwargs['validation_errors'] = errors
                    return func(*args, **kwargs)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator