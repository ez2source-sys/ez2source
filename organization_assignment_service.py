"""
Organization Assignment Service for Job2Hire
Handles automatic assignment of candidates to organizations based on various criteria
"""

from models import Organization, User
from app import db
import re
from typing import Optional, Dict, List


class OrganizationAssignmentService:
    """Service to handle automatic organization assignment for candidates"""
    
    @staticmethod
    def assign_candidate_to_organization(candidate_email: str, referrer_url: str = None, invitation_code: str = None) -> Optional[int]:
        """
        Assign candidate to organization based on multiple criteria:
        1. Invitation code (highest priority)
        2. Email domain matching
        3. Referrer URL domain
        4. Default organization fallback
        """
        
        # Priority 1: Invitation code assignment
        if invitation_code:
            org_id = OrganizationAssignmentService._assign_by_invitation_code(invitation_code)
            if org_id:
                return org_id
        
        # Priority 2: Email domain matching
        org_id = OrganizationAssignmentService._assign_by_email_domain(candidate_email)
        if org_id:
            return org_id
        
        # Priority 3: Referrer URL matching
        if referrer_url:
            org_id = OrganizationAssignmentService._assign_by_referrer_url(referrer_url)
            if org_id:
                return org_id
        
        # Priority 4: Default organization
        return OrganizationAssignmentService._get_or_create_default_organization()
    
    @staticmethod
    def _assign_by_invitation_code(invitation_code: str) -> Optional[int]:
        """Assign based on invitation code (to be implemented with invitation system)"""
        # This would check invitation codes in the database
        # For now, return None to fall back to other methods
        return None
    
    @staticmethod
    def _assign_by_email_domain(email: str) -> Optional[int]:
        """Assign based on email domain matching organization domains"""
        domain = email.split('@')[1].lower() if '@' in email else None
        if not domain:
            return None
        
        # Check if any organization has this domain configured
        # This could be expanded to include domain mapping in organization settings
        domain_mappings = {
            'techcorp.com': 'TechCorp Solutions',
            'innovate.io': 'InnovateTech',
            'startupxy.com': 'StartupXY',
            'example.com': 'Example Corp'
        }
        
        org_name = domain_mappings.get(domain)
        if org_name:
            org = Organization.query.filter_by(name=org_name).first()
            if org:
                return org.id
        
        return None
    
    @staticmethod
    def _assign_by_referrer_url(referrer_url: str) -> Optional[int]:
        """Assign based on referrer URL subdomain or path"""
        if not referrer_url:
            return None
        
        # Extract subdomain or organization identifier from URL
        # Example: https://techcorp.talentiq.com or https://talentiq.com/techcorp
        
        # Check for subdomain pattern
        subdomain_match = re.search(r'https?://([^.]+)\.talentiq\.com', referrer_url)
        if subdomain_match:
            subdomain = subdomain_match.group(1)
            org = Organization.query.filter_by(slug=subdomain).first()
            if org:
                return org.id
        
        # Check for path pattern
        path_match = re.search(r'talentiq\.com/([^/]+)', referrer_url)
        if path_match:
            path_org = path_match.group(1)
            org = Organization.query.filter_by(slug=path_org).first()
            if org:
                return org.id
        
        return None
    
    @staticmethod
    def _get_or_create_default_organization() -> int:
        """Get or create default organization for unassigned candidates"""
        default_org = Organization.query.filter_by(slug='open-pool').first()
        
        if not default_org:
            default_org = Organization(
                name='Open Candidate Pool',
                slug='open-pool',
                branding_config={'theme': 'default', 'color': '#6c757d'},
                subscription_plan='free',
                is_active=True
            )
            db.session.add(default_org)
            db.session.commit()
        
        return default_org.id
    
    @staticmethod
    def create_organization_specific_signup_link(org_slug: str) -> str:
        """Create organization-specific signup link"""
        return f"/register?org={org_slug}"
    
    @staticmethod
    def get_organization_from_signup_context(request_args: Dict) -> Optional[int]:
        """Extract organization from signup context (URL parameters)"""
        org_param = request_args.get('org')
        if org_param:
            org = Organization.query.filter_by(slug=org_param).first()
            if org:
                return org.id
        return None
    
    @staticmethod
    def update_unassigned_candidates():
        """Update existing candidates who don't have organization assignments"""
        unassigned_candidates = User.query.filter(
            User.role == 'candidate',
            User.organization_id.is_(None)
        ).all()
        
        updated_count = 0
        for candidate in unassigned_candidates:
            # Try to assign based on email domain
            org_id = OrganizationAssignmentService._assign_by_email_domain(candidate.email)
            
            # If no domain match, assign to default organization
            if not org_id:
                org_id = OrganizationAssignmentService._get_or_create_default_organization()
            
            candidate.organization_id = org_id
            updated_count += 1
        
        db.session.commit()
        return updated_count
    
    @staticmethod
    def get_organization_stats() -> Dict:
        """Get statistics about organization assignments"""
        total_candidates = User.query.filter_by(role='candidate').count()
        unassigned_candidates = User.query.filter(
            User.role == 'candidate',
            User.organization_id.is_(None)
        ).count()
        
        org_stats = db.session.query(
            Organization.name,
            db.func.count(User.id).label('candidate_count')
        ).outerjoin(User, User.organization_id == Organization.id).filter(
            User.role == 'candidate'
        ).group_by(Organization.id, Organization.name).all()
        
        return {
            'total_candidates': total_candidates,
            'unassigned_candidates': unassigned_candidates,
            'organization_breakdown': [
                {'name': stat[0], 'count': stat[1]} for stat in org_stats
            ]
        }


def setup_demo_organizations():
    """Set up demo organizations for testing"""
    demo_orgs = [
        {
            'name': 'TechCorp Solutions',
            'slug': 'techcorp',
            'branding_config': {'theme': 'blue', 'color': '#0066cc'}
        },
        {
            'name': 'InnovateTech',
            'slug': 'innovatetech', 
            'branding_config': {'theme': 'green', 'color': '#28a745'}
        },
        {
            'name': 'StartupXY',
            'slug': 'startupxy',
            'branding_config': {'theme': 'purple', 'color': '#6f42c1'}
        }
    ]
    
    for org_data in demo_orgs:
        existing_org = Organization.query.filter_by(slug=org_data['slug']).first()
        if not existing_org:
            org = Organization(
                name=org_data['name'],
                slug=org_data['slug'],
                branding_config=org_data['branding_config'],
                subscription_plan='trial',
                is_active=True
            )
            db.session.add(org)
    
    db.session.commit()