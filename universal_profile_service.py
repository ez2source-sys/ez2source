"""
Universal Profile Access Service for Job2Hire
Handles cross-organization profile access, public interviews, and employee status management
"""

from models import User, Interview, InterviewInvitation, Organization, TeamMember
from app import db
from typing import List, Dict, Optional, Tuple
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta


class InterviewInvitationData:
    """Simple data class to hold interview invitation information"""
    def __init__(self, data_dict):
        for key, value in data_dict.items():
            setattr(self, key, value)


class UniversalProfileService:
    """Service to handle universal profile access and cross-organization features"""
    
    @staticmethod
    def get_accessible_candidates_for_recruiter(recruiter_id: str, organization_id: int, 
                                              include_cross_org: bool = True, filters: Dict = None) -> List[Dict]:
        """
        Get all candidates accessible to a recruiter including cross-organization profiles with filtering
        """
        query = db.session.query(User).filter(User.role == 'candidate')
        
        # Initialize filter variables
        org_filter = None
        access_type_filter = None
        employee_status_filter = None
        
        # Apply filters if provided
        if filters:
            org_filter = filters.get('organization')
            access_type_filter = filters.get('access_type')
            employee_status_filter = filters.get('employee_status')
            
            # Skills filter
            if filters.get('skills'):
                skills_terms = [term.strip() for term in filters['skills'].split(',')]
                for term in skills_terms:
                    query = query.filter(or_(
                        User.skills.ilike(f'%{term}%'),
                        User.job_title.ilike(f'%{term}%')
                    ))
            
            # Location filter
            if filters.get('location'):
                location_terms = [term.strip() for term in filters['location'].split(',')]
                for term in location_terms:
                    query = query.filter(User.location.ilike(f'%{term}%'))
            
            # Experience filter
            if filters.get('experience_min'):
                try:
                    min_exp = int(filters['experience_min'])
                    query = query.filter(User.experience_years >= min_exp)
                except ValueError:
                    pass
                    
            if filters.get('experience_max'):
                try:
                    max_exp = int(filters['experience_max'])
                    query = query.filter(User.experience_years <= max_exp)
                except ValueError:
                    pass
            
            # Search filter (general search across multiple fields)
            if filters.get('search'):
                search_term = f"%{filters['search']}%"
                query = query.filter(or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    User.email.ilike(search_term),
                    User.job_title.ilike(search_term),
                    User.skills.ilike(search_term),
                    User.location.ilike(search_term)
                ))

        candidates = []
        
        # Get organization employees (highest priority)
        if not access_type_filter or access_type_filter == 'organization_employee':
            if not org_filter or org_filter in ['', 'same_org']:
                employee_query = query.filter(
                    User.organization_id == organization_id,
                    User.is_organization_employee == True
                )
                
                if employee_status_filter == 'non_employee':
                    employee_query = employee_query.filter(False)  # Skip employees
                elif employee_status_filter == 'employee':
                    pass  # Include all employees
                
                org_employees = employee_query.all()
                
                for candidate in org_employees:
                    candidates.append({
                        **UniversalProfileService._candidate_to_dict(candidate),
                        'access_type': 'organization_employee',
                        'priority': 'high',
                        'can_invite': True,
                        'interview_pipeline': 'employee'
                    })
        
        # Get organization-affiliated candidates (medium priority)
        if not access_type_filter or access_type_filter == 'organization_affiliated':
            if not org_filter or org_filter in ['', 'same_org']:
                affiliated_query = query.filter(
                    User.organization_id == organization_id,
                    User.is_organization_employee == False
                )
                
                if employee_status_filter == 'employee':
                    affiliated_query = affiliated_query.filter(False)  # Skip non-employees
                elif employee_status_filter == 'non_employee':
                    pass  # Include all non-employees
                
                org_candidates = affiliated_query.all()
                
                for candidate in org_candidates:
                    candidates.append({
                        **UniversalProfileService._candidate_to_dict(candidate),
                        'access_type': 'organization_affiliated',
                        'priority': 'medium',
                        'can_invite': True,
                        'interview_pipeline': 'standard'
                    })
        
        # Get cross-organization candidates with public profiles (if enabled)
        if include_cross_org and (not access_type_filter or access_type_filter == 'cross_organization'):
            if not org_filter or org_filter in ['', 'cross_org']:
                cross_org_query = query.filter(
                    or_(
                        User.organization_id != organization_id,
                        User.organization_id.is_(None)
                    ),
                    User.public_profile_enabled == True,
                    User.cross_org_accessible == True
                )
                
                if employee_status_filter == 'employee':
                    cross_org_query = cross_org_query.filter(User.is_organization_employee == True)
                elif employee_status_filter == 'non_employee':
                    cross_org_query = cross_org_query.filter(User.is_organization_employee == False)
                
                cross_org_candidates = cross_org_query.all()
                
                for candidate in cross_org_candidates:
                    candidates.append({
                        **UniversalProfileService._candidate_to_dict(candidate),
                        'access_type': 'cross_organization',
                        'priority': 'low',
                        'can_invite': True,
                        'interview_pipeline': 'public_only'
                    })
        
        return candidates
    
    @staticmethod
    def _candidate_to_dict(candidate: User) -> Dict:
        """Convert candidate to dictionary with profile information"""
        return {
            'id': candidate.id,
            'username': candidate.username,
            'email': candidate.email,
            'first_name': candidate.first_name or '',
            'last_name': candidate.last_name or '',
            'job_title': candidate.job_title or '',
            'bio': candidate.bio or '',
            'skills': candidate.skills,
            'experience_years': candidate.experience_years or 0,
            'organization_id': candidate.organization_id,
            'is_organization_employee': candidate.is_organization_employee,
            'public_profile_enabled': candidate.public_profile_enabled,
            'cross_org_accessible': candidate.cross_org_accessible,
            'profile_image_url': candidate.profile_image_url,
            'created_at': candidate.created_at
        }
    
    @staticmethod
    def send_public_interview_invitation(recruiter_id: str, candidate_id: str, 
                                       interview_id: int, message: str = None) -> Tuple[bool, str]:
        """
        Send a public interview invitation to any candidate across organizations
        """
        # Verify recruiter permissions
        recruiter = User.query.filter_by(id=recruiter_id, role='recruiter').first()
        if not recruiter:
            return False, "Recruiter not found"
        
        # Verify candidate exists and has public profile enabled
        candidate = User.query.filter_by(id=candidate_id, role='candidate').first()
        if not candidate:
            return False, "Candidate not found"
        
        if not candidate.public_profile_enabled:
            return False, "Candidate's profile is not publicly accessible"
        
        # Verify interview exists and supports public invitations
        interview = Interview.query.filter_by(id=interview_id).first()
        if not interview:
            return False, "Interview not found"
        
        if not interview.public_invitation_enabled:
            return False, "Interview does not support public invitations"
        
        # Check if candidate already has an invitation for this interview
        existing_invitation = InterviewInvitation.query.filter_by(
            interview_id=interview_id,
            candidate_id=candidate_id
        ).first()
        
        if existing_invitation:
            return False, "Candidate already has an invitation for this interview"
        
        # Check concurrent interview limits for candidate
        active_invitations = InterviewInvitation.query.filter_by(
            candidate_id=candidate_id,
            status='pending'
        ).count()
        
        if active_invitations >= 5:  # Configurable limit
            return False, "Candidate has reached maximum concurrent interview invitations"
        
        # Handle team structure adjustment for cross-org candidates
        if candidate.organization_id != recruiter.organization_id:
            UniversalProfileService._handle_team_structure_adjustment(candidate_id, interview_id)
        
        # Create the invitation
        invitation = InterviewInvitation(
            interview_id=interview_id,
            candidate_id=candidate_id,
            recruiter_id=recruiter_id,
            organization_id=recruiter.organization_id,  # Add required organization_id
            status='pending',
            message=message or f"You've been invited to participate in: {interview.title}",
            invitation_type='public' if candidate.organization_id != recruiter.organization_id else 'direct',
            is_cross_organization=candidate.organization_id != recruiter.organization_id,
            expires_at=datetime.now() + timedelta(days=7)
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        return True, "Public interview invitation sent successfully"
    
    @staticmethod
    def _handle_team_structure_adjustment(candidate_id: str, interview_id: int):
        """
        Remove candidate from existing team assignments when opting into cross-org interview
        """
        # Remove from any existing team memberships for this interview context
        TeamMember.query.filter_by(user_id=candidate_id).delete()
        db.session.commit()
    
    @staticmethod
    def get_candidate_public_interviews(candidate_id: str) -> List[Dict]:
        """
        Get all public interview invitations for a candidate across organizations
        """
        from sqlalchemy.orm import aliased
        
        # Create aliases to avoid ambiguity
        RecruiterUser = aliased(User)
        
        invitations = db.session.query(
            InterviewInvitation, 
            Interview, 
            RecruiterUser.username.label('recruiter_name'),
            Organization.name.label('organization_name')
        ).select_from(InterviewInvitation).join(
            Interview, Interview.id == InterviewInvitation.interview_id
        ).join(
            RecruiterUser, RecruiterUser.id == InterviewInvitation.recruiter_id
        ).join(
            Organization, Organization.id == Interview.organization_id
        ).filter(
            InterviewInvitation.candidate_id == candidate_id,
            InterviewInvitation.status == 'pending',
            Interview.is_active == True
        ).all()
        
        result = []
        for inv in invitations:
            invitation_data = {
                'invitation_id': inv.InterviewInvitation.id,
                'interview_id': inv.Interview.id,
                'interview_title': inv.Interview.title,
                'interview_type': inv.Interview.interview_type or 'public',
                'recruiter_name': inv.recruiter_name,
                'organization_name': inv.organization_name,
                'message': inv.InterviewInvitation.message or 'No message provided',
                'invitation_type': getattr(inv.InterviewInvitation, 'invitation_type', 'direct'),
                'is_cross_organization': getattr(inv.InterviewInvitation, 'is_cross_organization', False),
                'created_at': getattr(inv.InterviewInvitation, 'created_at', None),
                'expires_at': getattr(inv.InterviewInvitation, 'expires_at', None),
                'can_accept': True
            }
            result.append(InterviewInvitationData(invitation_data))
        
        return result
    
    @staticmethod
    def accept_public_interview_invitation(candidate_id: str, invitation_id: int) -> Tuple[bool, str]:
        """
        Accept a public interview invitation and handle multiple concurrent interviews
        """
        invitation = InterviewInvitation.query.filter_by(
            id=invitation_id,
            candidate_id=candidate_id,
            status='pending'
        ).first()
        
        if not invitation:
            return False, "Invitation not found or already processed"
        
        if invitation.expires_at and invitation.expires_at < datetime.now():
            return False, "Invitation has expired"
        
        # Update invitation status
        invitation.status = 'accepted'
        
        # Handle team adjustment for cross-org invitations
        if invitation.is_cross_organization:
            UniversalProfileService._handle_team_structure_adjustment(candidate_id, invitation.interview_id)
        
        db.session.commit()
        
        return True, "Interview invitation accepted successfully"
    
    @staticmethod
    def set_organization_employee_status(candidate_id: str, is_employee: bool) -> Tuple[bool, str]:
        """
        Set or update organization employee status for a candidate
        """
        candidate = User.query.filter_by(id=candidate_id, role='candidate').first()
        if not candidate:
            return False, "Candidate not found"
        
        candidate.is_organization_employee = is_employee
        
        # If setting as employee, ensure they have organization assignment
        if is_employee and not candidate.organization_id:
            return False, "Cannot set employee status without organization assignment"
        
        db.session.commit()
        
        return True, f"Organization employee status {'enabled' if is_employee else 'disabled'}"
    
    @staticmethod
    def toggle_public_profile_access(candidate_id: str, enable_public: bool, 
                                   enable_cross_org: bool = None) -> Tuple[bool, str]:
        """
        Toggle public profile access settings for a candidate
        """
        candidate = User.query.filter_by(id=candidate_id, role='candidate').first()
        if not candidate:
            return False, "Candidate not found"
        
        candidate.public_profile_enabled = enable_public
        
        if enable_cross_org is not None:
            candidate.cross_org_accessible = enable_cross_org
        
        db.session.commit()
        
        return True, "Profile access settings updated successfully"
    
    @staticmethod
    def get_organization_dashboard_candidates(organization_id: int) -> Dict:
        """
        Get mixed candidate pool for organization dashboard (employees + non-affiliated)
        """
        # Organization employees
        employees = User.query.filter_by(
            organization_id=organization_id,
            role='candidate',
            is_organization_employee=True
        ).all()
        
        # Non-affiliated candidates with public profiles
        public_candidates = User.query.filter(
            or_(
                User.organization_id != organization_id,
                User.organization_id.is_(None)
            ),
            User.role == 'candidate',
            User.public_profile_enabled == True,
            User.cross_org_accessible == True
        ).all()
        
        return {
            'organization_employees': [
                {**UniversalProfileService._candidate_to_dict(c), 'pipeline_type': 'employee'}
                for c in employees
            ],
            'public_candidates': [
                {**UniversalProfileService._candidate_to_dict(c), 'pipeline_type': 'public'}
                for c in public_candidates
            ],
            'total_employees': len(employees),
            'total_public': len(public_candidates)
        }