"""
Mobile-specific routes for Ez2Hire PWA
Provides mobile-optimized endpoints for candidate and recruiter apps
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import app, db
from models import User, JobPosting, JobApplication, Organization, Interview
import json

# Mobile App Landing Pages
@app.route('/mobile/candidate')
def mobile_candidate():
    """Landing page for EZ2Hire Candidate mobile app"""
    if current_user.is_authenticated and current_user.role == 'candidate':
        return redirect(url_for('candidate_dashboard'))
    return render_template('mobile/candidate_landing.html')

@app.route('/mobile/recruiter')
def mobile_recruiter():
    """Landing page for EZ2Hire Recruiting mobile app"""
    if current_user.is_authenticated and current_user.role in ['admin', 'recruiter', 'super_admin']:
        return redirect(url_for('admin_dashboard'))
    return render_template('mobile/recruiter_landing.html')

# PWA Installation APIs
@app.route('/api/pwa/install-stats', methods=['POST'])
def pwa_install_stats():
    """Track PWA installation statistics"""
    try:
        data = request.get_json()
        app_type = data.get('app_type', 'candidate')
        action = data.get('action', 'install')  # install, dismiss, uninstall
        
        # Log PWA installation for analytics
        # This could be stored in a database table for tracking
        app.logger.info(f"PWA {action}: {app_type} app")
        
        return jsonify({
            'success': True,
            'message': f'PWA {action} tracked'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Mobile-optimized API endpoints
@app.route('/api/mobile/dashboard-summary')
@login_required
def mobile_dashboard_summary():
    """Get dashboard summary data optimized for mobile"""
    try:
        if current_user.role == 'candidate':
            # Candidate dashboard data
            total_applications = db.session.query(JobApplication).filter_by(
                user_id=current_user.id
            ).count()
            
            pending_applications = db.session.query(JobApplication).filter_by(
                user_id=current_user.id,
                status='pending'
            ).count()
            
            interviews = db.session.query(Interview).join(JobApplication).filter(
                JobApplication.user_id == current_user.id
            ).count()
            
            # Quick stats for mobile
            summary = {
                'user_type': 'candidate',
                'total_applications': total_applications,
                'pending_applications': pending_applications,
                'interviews_scheduled': interviews,
                'profile_completion': calculate_profile_completion(current_user)
            }
            
        else:
            # Recruiter/Admin dashboard data
            if current_user.role == 'super_admin':
                total_candidates = db.session.query(User).filter_by(role='candidate').count()
                total_applications = db.session.query(JobApplication).count()
                active_jobs = db.session.query(JobPosting).filter_by(status='active').count()
            else:
                total_candidates = db.session.query(User).filter_by(
                    role='candidate',
                    organization_id=current_user.organization_id
                ).count()
                
                total_applications = db.session.query(JobApplication).join(JobPosting).filter(
                    JobPosting.organization_id == current_user.organization_id
                ).count()
                
                active_jobs = db.session.query(JobPosting).filter_by(
                    organization_id=current_user.organization_id,
                    status='active'
                ).count()
            
            summary = {
                'user_type': 'recruiter',
                'total_candidates': total_candidates,
                'total_applications': total_applications,
                'active_jobs': active_jobs,
                'organization': current_user.organization.name if current_user.organization else 'System'
            }
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        app.logger.error(f"Mobile dashboard error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Unable to load dashboard data'
        }), 500

@app.route('/api/mobile/quick-actions')
@login_required
def mobile_quick_actions():
    """Get quick actions for mobile app"""
    try:
        if current_user.role == 'candidate':
            actions = [
                {
                    'title': 'Search Jobs',
                    'icon': 'search',
                    'url': '/candidate/job-search',
                    'badge': get_new_jobs_count()
                },
                {
                    'title': 'My Applications',
                    'icon': 'file-text',
                    'url': '/candidate/applications',
                    'badge': get_pending_applications_count(current_user.id)
                },
                {
                    'title': 'Update Profile',
                    'icon': 'user',
                    'url': '/candidate/profile',
                    'badge': None
                },
                {
                    'title': 'Interview AI',
                    'icon': 'cpu',
                    'url': '/candidate/interview-setup',
                    'badge': None
                }
            ]
        else:
            actions = [
                {
                    'title': 'View Candidates',
                    'icon': 'users',
                    'url': '/admin/candidates',
                    'badge': get_new_candidates_count()
                },
                {
                    'title': 'Applications',
                    'icon': 'inbox',
                    'url': '/admin/applications',
                    'badge': get_pending_applications_count_admin()
                },
                {
                    'title': 'Schedule Interview',
                    'icon': 'calendar',
                    'url': '/admin/interviews',
                    'badge': None
                },
                {
                    'title': 'Analytics',
                    'icon': 'bar-chart',
                    'url': '/admin/analytics',
                    'badge': None
                }
            ]
        
        return jsonify({
            'success': True,
            'data': actions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Helper functions
def calculate_profile_completion(user):
    """Calculate user profile completion percentage"""
    fields = [
        user.first_name, user.last_name, user.email, user.phone,
        user.job_title, user.bio, user.skills, user.location
    ]
    completed = sum(1 for field in fields if field and str(field).strip())
    return int((completed / len(fields)) * 100)

def get_new_jobs_count():
    """Get count of new jobs posted in last 7 days"""
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    return db.session.query(JobPosting).filter(
        JobPosting.created_at >= week_ago,
        JobPosting.status == 'active'
    ).count()

def get_pending_applications_count(user_id):
    """Get pending applications count for a user"""
    return db.session.query(JobApplication).filter_by(
        user_id=user_id,
        status='pending'
    ).count()

def get_new_candidates_count():
    """Get new candidates registered in last 7 days"""
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    
    if current_user.role == 'super_admin':
        return db.session.query(User).filter(
            User.role == 'candidate',
            User.created_at >= week_ago
        ).count()
    else:
        return db.session.query(User).filter(
            User.role == 'candidate',
            User.organization_id == current_user.organization_id,
            User.created_at >= week_ago
        ).count()

def get_pending_applications_count_admin():
    """Get pending applications count for admin"""
    if current_user.role == 'super_admin':
        return db.session.query(JobApplication).filter_by(status='pending').count()
    else:
        return db.session.query(JobApplication).join(JobPosting).filter(
            JobPosting.organization_id == current_user.organization_id,
            JobApplication.status == 'pending'
        ).count()

# Mobile notification endpoints
@app.route('/api/mobile/notifications')
@login_required
def mobile_notifications():
    """Get mobile notifications"""
    try:
        notifications = []
        
        if current_user.role == 'candidate':
            # Get candidate notifications
            pending_interviews = db.session.query(Interview).join(JobApplication).filter(
                JobApplication.user_id == current_user.id,
                Interview.status == 'scheduled'
            ).count()
            
            if pending_interviews > 0:
                notifications.append({
                    'title': 'Upcoming Interviews',
                    'message': f'You have {pending_interviews} scheduled interview(s)',
                    'type': 'interview',
                    'action_url': '/candidate/interviews'
                })
        
        else:
            # Get recruiter notifications
            new_applications = get_pending_applications_count_admin()
            if new_applications > 0:
                notifications.append({
                    'title': 'New Applications',
                    'message': f'{new_applications} applications need review',
                    'type': 'application',
                    'action_url': '/admin/applications'
                })
        
        return jsonify({
            'success': True,
            'data': notifications
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# PWA offline support
@app.route('/offline.html')
def offline_page():
    """Offline page for PWA"""
    return render_template('mobile/offline.html')

if __name__ == '__main__':
    app.run(debug=True)