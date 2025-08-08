"""
HR Registration and Approval Service for Ez2Hire
Handles secure HR registration with organization verification and approval workflow
"""

import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from models import db, User, Organization, AuditLog
from enhanced_email_service import send_notification_email
import logging

class HRRegistrationService:
    """Service to handle HR registration with organization verification"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_hr_registration_request(self, 
                                     first_name: str,
                                     last_name: str,
                                     email: str,
                                     phone: str,
                                     organization_name: str,
                                     organization_email: str,
                                     job_title: str,
                                     linkedin_url: str = None,
                                     company_website: str = None,
                                     message: str = None) -> Dict:
        """
        Create an HR registration request with verification requirements
        
        Args:
            first_name: HR person's first name
            last_name: HR person's last name
            email: HR person's email (should match company domain)
            phone: HR person's phone number
            organization_name: Name of the organization
            organization_email: Official organization email for verification
            job_title: HR person's job title
            linkedin_url: Optional LinkedIn profile URL
            company_website: Optional company website URL
            message: Optional message from HR person
            
        Returns:
            Dict with registration status and next steps
        """
        try:
            # Check if organization exists
            existing_org = Organization.query.filter_by(name=organization_name).first()
            
            if existing_org:
                return self._handle_existing_organization_request(
                    existing_org, first_name, last_name, email, phone, 
                    job_title, linkedin_url, message
                )
            else:
                return self._handle_new_organization_request(
                    first_name, last_name, email, phone, organization_name,
                    organization_email, job_title, linkedin_url, 
                    company_website, message
                )
                
        except Exception as e:
            self.logger.error(f"Error creating HR registration request: {e}")
            return {
                'success': False,
                'message': 'Registration request failed due to system error',
                'error': str(e)
            }
    
    def _handle_existing_organization_request(self, 
                                            organization: Organization,
                                            first_name: str,
                                            last_name: str,
                                            email: str,
                                            phone: str,
                                            job_title: str,
                                            linkedin_url: str = None,
                                            message: str = None) -> Dict:
        """Handle HR registration for existing organization"""
        
        # Check if HR already exists for this organization
        existing_hr = User.query.filter_by(
            email=email,
            organization_id=organization.id
        ).first()
        
        if existing_hr:
            return {
                'success': False,
                'message': 'An account with this email already exists for this organization',
                'action': 'contact_support'
            }
        
        # Check email domain match
        email_domain = email.split('@')[1].lower()
        if not self._verify_email_domain(email_domain, organization.name):
            return {
                'success': False,
                'message': 'Email domain does not match organization domain',
                'action': 'verify_email',
                'details': 'Please use your official company email address'
            }
        
        # Get existing organization admins for approval
        org_admins = User.query.filter_by(
            organization_id=organization.id,
            role='admin'
        ).all()
        
        if not org_admins:
            # No admins exist - create super admin notification
            return self._create_super_admin_approval_request(
                organization, first_name, last_name, email, phone,
                job_title, linkedin_url, message
            )
        
        # Create approval request for existing org admins
        return self._create_org_admin_approval_request(
            organization, org_admins, first_name, last_name, email, 
            phone, job_title, linkedin_url, message
        )
    
    def _handle_new_organization_request(self,
                                       first_name: str,
                                       last_name: str,
                                       email: str,
                                       phone: str,
                                       organization_name: str,
                                       organization_email: str,
                                       job_title: str,
                                       linkedin_url: str = None,
                                       company_website: str = None,
                                       message: str = None) -> Dict:
        """Handle HR registration for new organization using Guest Organization system"""
        
        # Get or create Guest Organization
        guest_org = self._get_or_create_guest_organization()
        
        # Get or create Guest Organization Admin
        guest_admin = self._get_or_create_guest_admin(guest_org)
        
        # Create HR user immediately with Guest Organization assignment
        hr_user = self._create_guest_hr_user(
            guest_org.id, first_name, last_name, email, phone, 
            job_title, linkedin_url, organization_name, organization_email,
            company_website, message
        )
        
        # Send approval notification to Guest Admin
        self._notify_guest_admin_new_hr(guest_admin, hr_user, {
            'original_organization': organization_name,
            'organization_email': organization_email,
            'company_website': company_website,
            'message': message
        })
        
        return {
            'success': True,
            'message': 'Registration completed successfully',
            'action': 'guest_assignment',
            'details': f'You have been assigned to Guest Organization for review. A Guest Admin will evaluate your profile and may approve limited access.',
            'next_steps': [
                'You can now login with your credentials',
                'Guest Admin will review your profile',
                'Limited access granted initially',
                'Full access after organization verification'
            ]
        }
    
    def _verify_email_domain(self, email_domain: str, organization_name: str) -> bool:
        """Verify if email domain matches organization"""
        # Simple domain verification - can be enhanced
        common_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
        
        if email_domain in common_domains:
            return False  # Require corporate email
        
        # Check if domain contains organization name
        org_name_parts = organization_name.lower().replace(' ', '').replace('-', '')
        domain_parts = email_domain.lower().replace('.', '').replace('-', '')
        
        return org_name_parts in domain_parts or any(
            part in domain_parts for part in org_name_parts.split() if len(part) > 3
        )
    
    def _generate_verification_token(self) -> str:
        """Generate secure verification token"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
    
    def _create_super_admin_approval_request(self,
                                           organization: Organization,
                                           first_name: str,
                                           last_name: str,
                                           email: str,
                                           phone: str,
                                           job_title: str,
                                           linkedin_url: str = None,
                                           message: str = None) -> Dict:
        """Create approval request for super admin"""
        
        # Get super admin
        super_admin = User.query.filter_by(role='super_admin').first()
        
        if super_admin:
            # Send notification to super admin
            subject = f"HR Registration Request - {organization.name}"
            body = f"""
            New HR registration request requires your approval:
            
            Organization: {organization.name}
            Applicant: {first_name} {last_name}
            Email: {email}
            Phone: {phone}
            Job Title: {job_title}
            LinkedIn: {linkedin_url or 'Not provided'}
            Message: {message or 'Not provided'}
            
            Please review and approve/reject this request in the admin panel.
            """
            
            send_notification_email(super_admin.email, subject, 'notification', {
                'message': body,
                'user_name': 'Super Admin',
                'title': 'HR Registration Request',
                'action_url': 'https://ez2source.com/admin'
            })
        
        return {
            'success': True,
            'message': 'Registration request submitted for super admin approval',
            'action': 'wait_approval',
            'details': 'Your request has been sent to the platform administrators for review.',
            'next_steps': [
                'Wait for super admin review',
                'Receive approval/rejection notification',
                'If approved, receive login credentials'
            ]
        }
    
    def _create_org_admin_approval_request(self,
                                         organization: Organization,
                                         org_admins: List[User],
                                         first_name: str,
                                         last_name: str,
                                         email: str,
                                         phone: str,
                                         job_title: str,
                                         linkedin_url: str = None,
                                         message: str = None) -> Dict:
        """Create approval request for organization admins"""
        
        # Send notification to all org admins
        for admin in org_admins:
            subject = f"HR Registration Request - {organization.name}"
            body = f"""
            New HR registration request for your organization:
            
            Organization: {organization.name}
            Applicant: {first_name} {last_name}
            Email: {email}
            Phone: {phone}
            Job Title: {job_title}
            LinkedIn: {linkedin_url or 'Not provided'}
            Message: {message or 'Not provided'}
            
            Please review and approve/reject this request in your admin panel.
            """
            
            send_notification_email(admin.email, subject, 'notification', {
                'message': body,
                'user_name': admin.first_name or 'Admin',
                'title': 'HR Registration Request',
                'action_url': 'https://ez2source.com/admin'
            })
        
        return {
            'success': True,
            'message': 'Registration request submitted for organization admin approval',
            'action': 'wait_approval',
            'details': f'Your request has been sent to {organization.name} administrators for review.',
            'next_steps': [
                'Wait for organization admin review',
                'Receive approval/rejection notification',
                'If approved, receive login credentials'
            ]
        }
    
    def _send_organization_verification_email(self,
                                            organization_email: str,
                                            organization_name: str,
                                            verification_token: str,
                                            request_data: Dict):
        """Send verification email to organization"""
        
        subject = f"Verify HR Registration Request - {organization_name}"
        body = f"""
        An HR registration request has been submitted for {organization_name}:
        
        Applicant: {request_data['first_name']} {request_data['last_name']}
        Email: {request_data['email']}
        Job Title: {request_data['job_title']}
        
        To verify this request, please click the link below:
        [Verification Link would be implemented here]
        
        If you did not authorize this request, please ignore this email or contact support.
        """
        
        send_notification_email(organization_email, subject, 'notification', {
            'message': body,
            'user_name': 'Organization Administrator',
            'title': 'HR Registration Verification',
            'action_url': 'https://ez2source.com/'
        })
    
    def _get_or_create_guest_organization(self) -> Organization:
        """Get or create the Guest Organization"""
        guest_org = Organization.query.filter_by(name='Guest Organization').first()
        
        if not guest_org:
            guest_org = Organization(
                name='Guest Organization',
                slug='guest-organization',
                subscription_plan='guest',
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.session.add(guest_org)
            db.session.commit()
            self.logger.info("Created Guest Organization")
        
        return guest_org
    
    def _get_or_create_guest_admin(self, guest_org: Organization) -> User:
        """Get or create the Guest Organization Admin"""
        guest_admin = User.query.filter_by(
            organization_id=guest_org.id,
            role='admin'
        ).first()
        
        if not guest_admin:
            from werkzeug.security import generate_password_hash
            guest_admin = User(
                username='guest_admin',
                email='guest.admin@ez2source.com',
                password_hash=generate_password_hash('GuestAdmin2025!'),
                role='admin',
                first_name='Guest',
                last_name='Administrator',
                organization_id=guest_org.id,
                profile_completed=True,
                is_organization_employee=True,
                created_at=datetime.utcnow()
            )
            db.session.add(guest_admin)
            db.session.commit()
            self.logger.info("Created Guest Organization Admin")
        
        return guest_admin
    
    def _create_guest_hr_user(self, guest_org_id: int, first_name: str, last_name: str, 
                             email: str, phone: str, job_title: str, linkedin_url: str,
                             original_org_name: str, original_org_email: str,
                             company_website: str, message: str) -> User:
        """Create HR user assigned to Guest Organization"""
        from werkzeug.security import generate_password_hash
        import secrets
        import string
        
        # Generate temporary password
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create username from email
        username = email.split('@')[0] + '_guest_hr'
        
        # Normalize phone number
        from validation_service import ValidationService
        normalized_phone = ValidationService.normalize_phone(phone) if phone else None
        
        hr_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(temp_password),
            role='recruiter',
            first_name=first_name,
            last_name=last_name,
            phone=normalized_phone,
            organization_id=guest_org_id,
            profile_completed=True,
            is_organization_employee=True,
            bio=f"Guest HR from {original_org_name}. Job Title: {job_title}. " + 
                f"LinkedIn: {linkedin_url or 'Not provided'}. " +
                f"Original Organization Email: {original_org_email}. " +
                f"Website: {company_website or 'Not provided'}. " +
                f"Message: {message or 'Not provided'}",
            created_at=datetime.utcnow()
        )
        
        db.session.add(hr_user)
        db.session.commit()
        
        # Send credentials to HR user
        self._send_guest_hr_credentials(hr_user, temp_password, original_org_name)
        
        return hr_user
    
    def _notify_guest_admin_new_hr(self, guest_admin: User, hr_user: User, org_info: Dict):
        """Notify Guest Admin about new HR user"""
        subject = f"New Guest HR Profile - {hr_user.first_name} {hr_user.last_name}"
        body = f"""
        New HR professional has been assigned to Guest Organization:
        
        HR Details:
        Name: {hr_user.first_name} {hr_user.last_name}
        Email: {hr_user.email}
        Phone: {hr_user.phone or 'Not provided'}
        Username: {hr_user.username}
        
        Original Organization Information:
        Organization: {org_info['original_organization']}
        Organization Email: {org_info['organization_email']}
        Website: {org_info['company_website'] or 'Not provided'}
        Message: {org_info['message'] or 'Not provided'}
        
        Actions Available:
        1. Review the HR profile in Guest Organization
        2. Grant limited access permissions
        3. Approve for full access if organization is verified
        4. Transfer to appropriate organization when available
        
        Please log in to review and manage this Guest HR profile.
        """
        
        send_notification_email(guest_admin.email, subject, 'notification', {
            'message': body,
            'user_name': 'Guest Admin',
            'title': 'New HR Registration in Guest Organization',
            'action_url': 'https://ez2source.com/admin'
        })
    
    def _send_guest_hr_credentials(self, hr_user: User, temp_password: str, original_org_name: str):
        """Send login credentials to Guest HR user"""
        subject = f"Welcome to Ez2source - Guest HR Access"
        body = f"""
        Welcome to Ez2source, {hr_user.first_name}!
        
        Your HR registration for {original_org_name} has been processed and you have been assigned to our Guest Organization system for review.
        
        Login Credentials:
        Username: {hr_user.username}
        Password: {temp_password}
        
        Next Steps:
        1. Log in to your account
        2. Complete your profile if needed
        3. Guest Admin will review your profile
        4. Limited access is available immediately
        5. Full access will be granted after verification
        
        Important Notes:
        - You are currently in "Guest Organization" for review
        - Your profile will be evaluated by our Guest Admin
        - Once your organization is verified, you may be transferred to the appropriate organization
        - Please change your password after first login
        
        If you have any questions, please contact our support team.
        
        Welcome to Ez2source!
        """
        
        send_notification_email(hr_user.email, subject, 'notification', {
            'message': body,
            'user_name': hr_user.first_name or 'HR Professional',
            'title': 'HR Registration Confirmation',
            'action_url': 'https://ez2source.com/login'
        })

# Service instance
hr_registration_service = HRRegistrationService()