"""
Form Validation Service for Ez2Hire
Provides comprehensive server-side validation with descriptive error messages
"""

import re
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from flask import request, session, current_app
from models import User, Organization, db


class FormValidationService:
    """Comprehensive form validation service with descriptive error messages"""
    
    def __init__(self):
        self.errors = {}
        self.field_names = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email',
            'phone': 'Phone Number',
            'password': 'Password',
            'confirm_password': 'Confirm Password',
            'bio': 'Bio',
            'skills': 'Skills',
            'experience': 'Experience',
            'education': 'Education',
            'linkedin_url': 'LinkedIn URL',
            'github_url': 'GitHub URL',
            'portfolio_url': 'Portfolio URL',
            'salary_expectation': 'Salary Expectation',
            'company_name': 'Company Name',
            'job_title': 'Job Title',
            'location': 'Location',
            'username': 'Username',
            'organization_name': 'Organization Name',
            'website': 'Website',
            'description': 'Description',
            'industry': 'Industry',
            'size': 'Company Size',
            'founded_year': 'Founded Year',
            'address': 'Address',
            'city': 'City',
            'state': 'State',
            'country': 'Country',
            'postal_code': 'Postal Code'
        }
        
        # Validation patterns
        self.patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^[\+]?[1-9][\d]{0,15}$',
            'url': r'^https?://[^\s/$.?#].[^\s]*$',
            'linkedin_url': r'^https?://(www\.)?linkedin\.com/(in|pub|profile)/[a-zA-Z0-9-]+/?$',
            'github_url': r'^https?://(www\.)?github\.com/[a-zA-Z0-9-]+/?$',
            'username': r'^[a-zA-Z0-9_]{3,20}$',
            'password': r'^.{8,}$',
            'year': r'^(19|20)\d{2}$',
            'postal_code': r'^[0-9]{5}(-[0-9]{4})?$|^[A-Z0-9]{3}\s?[A-Z0-9]{3}$'
        }
    
    def validate_form(self, form_data: Dict[str, Any], validation_rules: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Validate form data according to validation rules
        
        Args:
            form_data: Dictionary of form field values
            validation_rules: Dictionary of field validation rules
            
        Returns:
            Dictionary with validation results and errors
        """
        self.errors = {}
        
        for field, rules in validation_rules.items():
            field_value = form_data.get(field, '').strip() if form_data.get(field) else ''
            
            for rule in rules:
                if not self._validate_field(field, field_value, rule):
                    break  # Stop validation on first error for this field
        
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'field_errors': self._format_field_errors()
        }
    
    def _validate_field(self, field: str, value: str, rule: str) -> bool:
        """Validate a single field against a rule"""
        field_display_name = self.field_names.get(field, field.replace('_', ' ').title())
        
        if rule == 'required':
            if not value:
                self.errors[field] = f"{field_display_name} is required"
                return False
        
        elif rule == 'email':
            if value and not re.match(self.patterns['email'], value):
                self.errors[field] = "Please enter a valid email address"
                return False
        
        elif rule == 'phone':
            if value and not re.match(self.patterns['phone'], value):
                self.errors[field] = "Please enter a valid phone number"
                return False
        
        elif rule == 'url':
            if value and not re.match(self.patterns['url'], value):
                self.errors[field] = "Please enter a valid URL"
                return False
        
        elif rule == 'linkedin_url':
            if value and not re.match(self.patterns['linkedin_url'], value):
                self.errors[field] = "Please enter a valid LinkedIn profile URL"
                return False
        
        elif rule == 'github_url':
            if value and not re.match(self.patterns['github_url'], value):
                self.errors[field] = "Please enter a valid GitHub profile URL"
                return False
        
        elif rule == 'username':
            if value and not re.match(self.patterns['username'], value):
                self.errors[field] = "Username must be 3-20 characters long and contain only letters, numbers, and underscores"
                return False
        
        elif rule == 'password':
            if value and not re.match(self.patterns['password'], value):
                self.errors[field] = "Password must be at least 8 characters long"
                return False
        
        elif rule == 'confirm_password':
            password = request.form.get('password', '')
            if value and value != password:
                self.errors[field] = "Passwords do not match"
                return False
        
        elif rule == 'unique_email':
            if value and User.query.filter_by(email=value).first():
                self.errors[field] = "This email address is already registered"
                return False
        
        elif rule == 'unique_username':
            if value and User.query.filter_by(username=value).first():
                self.errors[field] = "This username is already taken"
                return False
        
        elif rule == 'unique_phone':
            if value and User.query.filter_by(phone=value).first():
                self.errors[field] = "This phone number is already registered"
                return False
        
        elif rule == 'min_length':
            min_length = int(rule.split(':')[1]) if ':' in rule else 3
            if value and len(value) < min_length:
                self.errors[field] = f"{field_display_name} must be at least {min_length} characters long"
                return False
        
        elif rule == 'max_length':
            max_length = int(rule.split(':')[1]) if ':' in rule else 255
            if value and len(value) > max_length:
                self.errors[field] = f"{field_display_name} must be no more than {max_length} characters long"
                return False
        
        elif rule == 'numeric':
            if value and not value.isdigit():
                self.errors[field] = f"{field_display_name} must be a number"
                return False
        
        elif rule == 'year':
            if value and not re.match(self.patterns['year'], value):
                self.errors[field] = "Please enter a valid year (e.g., 2024)"
                return False
        
        elif rule == 'postal_code':
            if value and not re.match(self.patterns['postal_code'], value):
                self.errors[field] = "Please enter a valid postal code"
                return False
        
        elif rule.startswith('min_value'):
            min_value = int(rule.split(':')[1])
            if value and (not value.isdigit() or int(value) < min_value):
                self.errors[field] = f"{field_display_name} must be at least {min_value}"
                return False
        
        elif rule.startswith('max_value'):
            max_value = int(rule.split(':')[1])
            if value and (not value.isdigit() or int(value) > max_value):
                self.errors[field] = f"{field_display_name} must be no more than {max_value}"
                return False
        
        return True
    
    def _format_field_errors(self) -> Dict[str, str]:
        """Format errors for frontend display"""
        formatted_errors = {}
        for field, error in self.errors.items():
            formatted_errors[field] = {
                'message': error,
                'field_name': self.field_names.get(field, field.replace('_', ' ').title())
            }
        return formatted_errors
    
    def get_validation_rules(self, form_type: str) -> Dict[str, List[str]]:
        """Get validation rules for specific form types"""
        rules = {
            'candidate_register': {
                'first_name': ['required', 'min_length:2', 'max_length:50'],
                'last_name': ['required', 'min_length:2', 'max_length:50'],
                'email': ['required', 'email', 'unique_email'],
                'phone': ['required', 'phone', 'unique_phone'],
                'password': ['required', 'password'],
                'confirm_password': ['required', 'confirm_password']
            },
            'candidate_profile': {
                'first_name': ['required', 'min_length:2', 'max_length:50'],
                'last_name': ['required', 'min_length:2', 'max_length:50'],
                'email': ['required', 'email'],
                'phone': ['required', 'phone'],
                'bio': ['max_length:1000'],
                'skills': ['max_length:500'],
                'experience': ['max_length:2000'],
                'education': ['max_length:1000'],
                'linkedin_url': ['linkedin_url'],
                'github_url': ['github_url'],
                'portfolio_url': ['url'],
                'salary_expectation': ['required']
            },
            'user_invitation': {
                'first_name': ['required', 'min_length:2', 'max_length:50'],
                'last_name': ['required', 'min_length:2', 'max_length:50'],
                'email': ['required', 'email', 'unique_email'],
                'phone': ['phone'],
                'role': ['required']
            },
            'organization_create': {
                'name': ['required', 'min_length:2', 'max_length:100'],
                'description': ['max_length:1000'],
                'website': ['url'],
                'industry': ['max_length:100'],
                'size': ['max_length:50'],
                'founded_year': ['year'],
                'address': ['max_length:200'],
                'city': ['max_length:100'],
                'state': ['max_length:100'],
                'country': ['max_length:100'],
                'postal_code': ['postal_code']
            },
            'login': {
                'username': ['required'],
                'password': ['required']
            },
            'interview_create': {
                'title': ['required', 'min_length:3', 'max_length:200'],
                'description': ['max_length:1000'],
                'duration': ['required', 'numeric', 'min_value:5', 'max_value:180']
            },
            'job_posting': {
                'title': ['required', 'min_length:3', 'max_length:200'],
                'description': ['required', 'min_length:50', 'max_length:5000'],
                'requirements': ['max_length:2000'],
                'benefits': ['max_length:1000'],
                'salary_min': ['numeric', 'min_value:0'],
                'salary_max': ['numeric', 'min_value:0'],
                'location': ['required', 'max_length:100'],
                'job_type': ['required'],
                'experience_level': ['required']
            }
        }
        
        return rules.get(form_type, {})
    
    def validate_json_field(self, field_name: str, json_data: str) -> bool:
        """Validate JSON field format"""
        try:
            if json_data:
                json.loads(json_data)
            return True
        except (json.JSONDecodeError, TypeError):
            self.errors[field_name] = f"Invalid {self.field_names.get(field_name, field_name)} format"
            return False
    
    def validate_date_field(self, field_name: str, date_str: str) -> bool:
        """Validate date field format"""
        try:
            if date_str:
                datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            self.errors[field_name] = f"Please enter a valid date for {self.field_names.get(field_name, field_name)}"
            return False
    
    def validate_file_upload(self, field_name: str, file, allowed_extensions: List[str], max_size_mb: int = 5) -> bool:
        """Validate file upload"""
        if not file:
            return True
        
        # Check file extension
        filename = file.filename.lower()
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            self.errors[field_name] = f"Only {', '.join(allowed_extensions)} files are allowed"
            return False
        
        # Check file size
        file.seek(0, 2)  # Move to end of file
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > max_size_mb * 1024 * 1024:
            self.errors[field_name] = f"File size must be less than {max_size_mb}MB"
            return False
        
        return True


def validate_form_data(form_data: Dict[str, Any], form_type: str) -> Dict[str, Any]:
    """
    Validate form data for a specific form type
    
    Args:
        form_data: Dictionary of form field values
        form_type: Type of form being validated
        
    Returns:
        Dictionary with validation results and errors
    """
    validator = FormValidationService()
    validation_rules = validator.get_validation_rules(form_type)
    return validator.validate_form(form_data, validation_rules)


def get_form_errors_html(errors: Dict[str, str]) -> str:
    """
    Generate HTML for displaying form errors
    
    Args:
        errors: Dictionary of field errors
        
    Returns:
        HTML string for displaying errors
    """
    if not errors:
        return ""
    
    html = '<div class="form-general-error alert alert-danger">'
    html += '<strong>Please correct the following errors:</strong>'
    html += '<ul class="mb-0 mt-2">'
    
    for field, error in errors.items():
        html += f'<li>{error}</li>'
    
    html += '</ul></div>'
    return html


def add_validation_attributes(form_type: str) -> Dict[str, str]:
    """
    Get HTML5 validation attributes for form fields
    
    Args:
        form_type: Type of form
        
    Returns:
        Dictionary of field attributes for client-side validation
    """
    validator = FormValidationService()
    rules = validator.get_validation_rules(form_type)
    attributes = {}
    
    for field, field_rules in rules.items():
        field_attrs = []
        
        if 'required' in field_rules:
            field_attrs.append('required')
        
        if 'email' in field_rules:
            field_attrs.append('data-validate="email"')
        
        if 'phone' in field_rules:
            field_attrs.append('data-validate="phone"')
        
        if 'url' in field_rules:
            field_attrs.append('data-validate="url"')
        
        if 'password' in field_rules:
            field_attrs.append('data-validate="password"')
        
        if 'confirm_password' in field_rules:
            field_attrs.append('data-validate="password_confirm"')
        
        # Add field name for error messages
        field_display_name = validator.field_names.get(field, field.replace('_', ' ').title())
        field_attrs.append(f'data-field-name="{field_display_name}"')
        
        attributes[field] = ' '.join(field_attrs)
    
    return attributes