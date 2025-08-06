"""
Advanced Analytics & Reporting Service for Ez2Hire
Real-time recruitment metrics, candidate pipeline analytics, and cross-organizational insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, text, and_, or_
from sqlalchemy.orm import joinedload
from app import db
from models import (
    User, Organization, JobPosting, JobApplication, Interview, InterviewResponse,
    TechnicalInterviewAssignment, TechnicalInterviewFeedback, AuditLog
)

class AdvancedAnalyticsService:
    """Comprehensive analytics service for recruitment metrics and insights"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_recruitment_metrics_dashboard(self, user_id: int, organization_id: Optional[int] = None) -> Dict:
        """
        Get comprehensive recruitment metrics dashboard
        
        Args:
            user_id: Current user ID
            organization_id: Organization ID (None for super admin cross-org view)
            
        Returns:
            Dict with complete recruitment metrics
        """
        try:
            current_user = User.query.get(user_id)
            if not current_user:
                return self._get_empty_metrics()
            
            # Determine scope (organization-specific or cross-organizational)
            is_super_admin = current_user.role == 'super_admin'
            target_org_id = None if is_super_admin else (organization_id or current_user.organization_id)
            
            # Get time periods
            now = datetime.utcnow()
            last_30_days = now - timedelta(days=30)
            last_7_days = now - timedelta(days=7)
            
            # Build base queries with organization filter
            base_filter = [] if target_org_id is None else [User.organization_id == target_org_id]
            
            # Core metrics
            total_candidates = self._get_candidate_count(base_filter)
            total_jobs = self._get_job_count(target_org_id)
            total_applications = self._get_application_count(target_org_id)
            total_interviews = self._get_interview_count(target_org_id)
            
            # Pipeline metrics
            pipeline_metrics = self._get_pipeline_metrics(target_org_id, last_30_days)
            
            # Performance metrics
            performance_metrics = self._get_performance_metrics(target_org_id, last_30_days)
            
            # Trend analysis
            trend_analysis = self._get_trend_analysis(target_org_id, last_30_days, last_7_days)
            
            # Interview analytics
            interview_analytics = self._get_interview_analytics(target_org_id, last_30_days)
            
            # Cross-organizational insights (super admin only)
            cross_org_insights = self._get_cross_org_insights() if is_super_admin else {}
            
            return {
                'overview': {
                    'total_candidates': total_candidates,
                    'total_jobs': total_jobs,
                    'total_applications': total_applications,
                    'total_interviews': total_interviews,
                    'scope': 'cross_organizational' if is_super_admin else 'organization',
                    'organization_name': None if is_super_admin else current_user.organization.name,
                    'generated_at': now.isoformat()
                },
                'pipeline_metrics': pipeline_metrics,
                'performance_metrics': performance_metrics,
                'trend_analysis': trend_analysis,
                'interview_analytics': interview_analytics,
                'cross_org_insights': cross_org_insights
            }
            
        except Exception as e:
            self.logger.error(f"Error generating recruitment metrics: {e}")
            return self._get_empty_metrics()
    
    def _get_candidate_count(self, base_filter: List) -> int:
        """Get total candidate count with filters"""
        query = db.session.query(User).filter(User.role == 'candidate')
        if base_filter:
            query = query.filter(and_(*base_filter))
        return query.count()
    
    def _get_job_count(self, organization_id: Optional[int]) -> int:
        """Get total job posting count"""
        query = db.session.query(JobPosting)
        if organization_id:
            # Note: JobPosting doesn't have organization_id, skipping organization filter for job count
            pass
        return query.count()
    
    def _get_application_count(self, organization_id: Optional[int]) -> int:
        """Get total application count"""
        query = db.session.query(JobApplication)
        if organization_id:
            # Note: JobPosting doesn't have organization_id, skipping organization filter for applications
            pass
        return query.count()
    
    def _get_interview_count(self, organization_id: Optional[int]) -> int:
        """Get total interview count"""
        query = db.session.query(Interview)
        if organization_id:
            query = query.filter(Interview.organization_id == organization_id)
        return query.count()
    
    def _get_pipeline_metrics(self, organization_id: Optional[int], since_date: datetime) -> Dict:
        """Get candidate pipeline metrics"""
        try:
            # Application status distribution
            status_query = db.session.query(
                JobApplication.status,
                func.count(JobApplication.id).label('count')
            )
            
            if organization_id:
                # Note: JobPosting doesn't have organization_id, skipping organization filter
                pass
            
            status_distribution = dict(status_query.group_by(JobApplication.status).all())
            
            # Recent applications
            recent_apps_query = db.session.query(JobApplication).filter(
                JobApplication.application_date >= since_date
            )
            
            if organization_id:
                # Note: JobPosting doesn't have organization_id, skipping organization filter
                pass
            
            recent_applications = recent_apps_query.count()
            
            # Conversion rates
            total_apps = sum(status_distribution.values()) or 1
            interview_rate = (status_distribution.get('interview', 0) / total_apps) * 100
            offer_rate = (status_distribution.get('offer', 0) / total_apps) * 100
            
            return {
                'status_distribution': status_distribution,
                'recent_applications': recent_applications,
                'conversion_rates': {
                    'interview_rate': round(interview_rate, 2),
                    'offer_rate': round(offer_rate, 2)
                },
                'total_in_pipeline': total_apps
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating pipeline metrics: {e}")
            return {'status_distribution': {}, 'recent_applications': 0, 'conversion_rates': {}, 'total_in_pipeline': 0}
    
    def _get_performance_metrics(self, organization_id: Optional[int], since_date: datetime) -> Dict:
        """Get recruitment performance metrics"""
        try:
            # Average time to hire
            completed_apps = db.session.query(JobApplication).filter(
                JobApplication.status.in_(['offer', 'hired']),
                JobApplication.application_date >= since_date
            )
            
            if organization_id:
                # Note: JobPosting doesn't have organization_id, skipping organization filter
                pass
            
            avg_time_to_hire = 0
            completed_count = 0
            
            for app in completed_apps:
                if app.response_received_date:
                    days_diff = (app.response_received_date - app.application_date).days
                    avg_time_to_hire += days_diff
                    completed_count += 1
            
            avg_time_to_hire = avg_time_to_hire / completed_count if completed_count > 0 else 0
            
            # Interview success rate
            interview_responses = db.session.query(InterviewResponse).filter(
                InterviewResponse.completed_at >= since_date
            )
            
            if organization_id:
                interview_responses = interview_responses.join(Interview).filter(
                    Interview.organization_id == organization_id
                )
            
            total_interviews = interview_responses.count()
            successful_interviews = interview_responses.filter(
                InterviewResponse.ai_score >= 70.0
            ).count()
            
            success_rate = (successful_interviews / total_interviews * 100) if total_interviews > 0 else 0
            
            return {
                'avg_time_to_hire': round(avg_time_to_hire, 1),
                'interview_success_rate': round(success_rate, 2),
                'total_interviews_conducted': total_interviews,
                'successful_interviews': successful_interviews
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {'avg_time_to_hire': 0, 'interview_success_rate': 0, 'total_interviews_conducted': 0, 'successful_interviews': 0}
    
    def _get_trend_analysis(self, organization_id: Optional[int], last_30_days: datetime, last_7_days: datetime) -> Dict:
        """Get trend analysis for applications and interviews"""
        try:
            # Application trends
            apps_30_days = db.session.query(JobApplication).filter(
                JobApplication.application_date >= last_30_days
            )
            apps_7_days = db.session.query(JobApplication).filter(
                JobApplication.application_date >= last_7_days
            )
            
            if organization_id:
                # Note: JobPosting doesn't have organization_id, skipping organization filter
                pass
            
            applications_30_days = apps_30_days.count()
            applications_7_days = apps_7_days.count()
            
            # Calculate weekly trend
            weekly_avg = applications_30_days / 4.3  # 30 days ÷ 7 days
            trend_percentage = ((applications_7_days - weekly_avg) / weekly_avg * 100) if weekly_avg > 0 else 0
            
            return {
                'applications_last_30_days': applications_30_days,
                'applications_last_7_days': applications_7_days,
                'weekly_trend_percentage': round(trend_percentage, 2),
                'trend_direction': 'up' if trend_percentage > 0 else 'down' if trend_percentage < 0 else 'stable'
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating trend analysis: {e}")
            return {'applications_last_30_days': 0, 'applications_last_7_days': 0, 'weekly_trend_percentage': 0, 'trend_direction': 'stable'}
    
    def _get_interview_analytics(self, organization_id: Optional[int], since_date: datetime) -> Dict:
        """Get detailed interview analytics"""
        try:
            # Interview performance by type
            interview_query = db.session.query(Interview).filter(
                Interview.created_at >= since_date
            )
            
            if organization_id:
                interview_query = interview_query.filter(Interview.organization_id == organization_id)
            
            # Interview completion rates
            total_interviews = interview_query.count()
            completed_interviews = db.session.query(InterviewResponse).join(Interview).filter(
                Interview.created_at >= since_date,
                InterviewResponse.completed_at.isnot(None)
            )
            
            if organization_id:
                completed_interviews = completed_interviews.filter(Interview.organization_id == organization_id)
            
            completion_rate = (completed_interviews.count() / total_interviews * 100) if total_interviews > 0 else 0
            
            # Average interview scores
            avg_score_query = db.session.query(func.avg(InterviewResponse.ai_score)).join(Interview).filter(
                Interview.created_at >= since_date,
                InterviewResponse.ai_score.isnot(None)
            )
            
            if organization_id:
                avg_score_query = avg_score_query.filter(Interview.organization_id == organization_id)
            
            avg_score = avg_score_query.scalar() or 0
            
            return {
                'total_interviews': total_interviews,
                'completed_interviews': completed_interviews.count(),
                'completion_rate': round(completion_rate, 2),
                'average_score': round(avg_score, 2),
                'score_distribution': self._get_score_distribution(organization_id, since_date)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating interview analytics: {e}")
            return {'total_interviews': 0, 'completed_interviews': 0, 'completion_rate': 0, 'average_score': 0, 'score_distribution': {}}
    
    def _get_score_distribution(self, organization_id: Optional[int], since_date: datetime) -> Dict:
        """Get interview score distribution"""
        try:
            score_query = db.session.query(InterviewResponse.ai_score).join(Interview).filter(
                Interview.created_at >= since_date,
                InterviewResponse.ai_score.isnot(None)
            )
            
            if organization_id:
                score_query = score_query.filter(Interview.organization_id == organization_id)
            
            scores = [score[0] for score in score_query.all()]
            
            # Categorize scores
            excellent = len([s for s in scores if s >= 90])
            good = len([s for s in scores if 70 <= s < 90])
            fair = len([s for s in scores if 50 <= s < 70])
            poor = len([s for s in scores if s < 50])
            
            return {
                'excellent': excellent,  # 90-100
                'good': good,           # 70-89
                'fair': fair,           # 50-69
                'poor': poor            # <50
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating score distribution: {e}")
            return {'excellent': 0, 'good': 0, 'fair': 0, 'poor': 0}
    
    def _get_cross_org_insights(self) -> Dict:
        """Get cross-organizational insights for super admins"""
        try:
            # Organization performance comparison
            org_stats = db.session.query(
                Organization.name,
                func.count(User.id).label('total_candidates'),
                func.count(JobPosting.id).label('total_jobs')
            ).outerjoin(User, User.organization_id == Organization.id).group_by(Organization.id, Organization.name).all()
            
            # Top performing organizations
            top_orgs = sorted(org_stats, key=lambda x: x.total_candidates, reverse=True)[:5]
            
            return {
                'total_organizations': len(org_stats),
                'top_performing_orgs': [
                    {
                        'name': org.name,
                        'candidates': org.total_candidates,
                        'jobs': org.total_jobs
                    }
                    for org in top_orgs
                ],
                'cross_org_metrics': {
                    'total_platform_candidates': sum(org.total_candidates for org in org_stats),
                    'total_platform_jobs': sum(org.total_jobs for org in org_stats)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating cross-org insights: {e}")
            return {'total_organizations': 0, 'top_performing_orgs': [], 'cross_org_metrics': {}}
    
    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            'overview': {
                'total_candidates': 0,
                'total_jobs': 0,
                'total_applications': 0,
                'total_interviews': 0,
                'scope': 'organization',
                'organization_name': None,
                'generated_at': datetime.utcnow().isoformat()
            },
            'pipeline_metrics': {'status_distribution': {}, 'recent_applications': 0, 'conversion_rates': {}, 'total_in_pipeline': 0},
            'performance_metrics': {'avg_time_to_hire': 0, 'interview_success_rate': 0, 'total_interviews_conducted': 0, 'successful_interviews': 0},
            'trend_analysis': {'applications_last_30_days': 0, 'applications_last_7_days': 0, 'weekly_trend_percentage': 0, 'trend_direction': 'stable'},
            'interview_analytics': {'total_interviews': 0, 'completed_interviews': 0, 'completion_rate': 0, 'average_score': 0, 'score_distribution': {}},
            'cross_org_insights': {}
        }

def get_recruitment_dashboard_data(user_id: int, organization_id: Optional[int] = None) -> Dict:
    """
    Get comprehensive recruitment dashboard data
    
    Args:
        user_id: Current user ID
        organization_id: Optional organization ID for filtering
        
    Returns:
        Dict with complete dashboard metrics
    """
    service = AdvancedAnalyticsService()
    return service.get_recruitment_metrics_dashboard(user_id, organization_id)

def get_candidate_pipeline_analytics(user_id: int, organization_id: Optional[int] = None) -> Dict:
    """
    Get detailed candidate pipeline analytics
    
    Args:
        user_id: Current user ID
        organization_id: Optional organization ID for filtering
        
    Returns:
        Dict with pipeline analytics
    """
    service = AdvancedAnalyticsService()
    dashboard_data = service.get_recruitment_metrics_dashboard(user_id, organization_id)
    
    return {
        'pipeline_metrics': dashboard_data['pipeline_metrics'],
        'performance_metrics': dashboard_data['performance_metrics'],
        'trend_analysis': dashboard_data['trend_analysis']
    }

def get_interview_performance_tracking(user_id: int, organization_id: Optional[int] = None) -> Dict:
    """
    Get interview performance tracking data
    
    Args:
        user_id: Current user ID
        organization_id: Optional organization ID for filtering
        
    Returns:
        Dict with interview performance data
    """
    service = AdvancedAnalyticsService()
    dashboard_data = service.get_recruitment_metrics_dashboard(user_id, organization_id)
    
    return {
        'interview_analytics': dashboard_data['interview_analytics'],
        'performance_metrics': dashboard_data['performance_metrics']
    }