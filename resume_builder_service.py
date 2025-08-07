"""
AI-Powered Resume Builder Service
Inspired by Huntr.co's AI resume builder with ATS optimization
"""

import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResumeBuilderAI:
    """AI service for intelligent resume building and optimization"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.logger = logging.getLogger(__name__)
    
    def generate_professional_summary(self, job_title: str, experience_years: int, 
                                    key_skills: List[str], industry: str = "") -> Dict[str, Any]:
        """
        Generate AI-powered professional summary
        Similar to Huntr's AI resume summary generator
        """
        try:
            skills_text = ", ".join(key_skills[:8]) if key_skills else "various technical skills"
            
            prompt = f"""
            Create a compelling professional summary for a resume. Use this information:
            - Job Title: {job_title}
            - Years of Experience: {experience_years}
            - Key Skills: {skills_text}
            - Industry: {industry or "technology"}
            
            Requirements:
            1. Write in third person
            2. Highlight quantifiable achievements where possible
            3. Include relevant keywords for ATS optimization
            4. Keep it 3-4 sentences long
            5. Make it compelling and professional
            6. Focus on value proposition to employers
            
            Also suggest a professional headline (job title + key value proposition).
            
            Respond with JSON:
            {{
                "professional_summary": "3-4 sentence professional summary",
                "headline": "Professional headline (under 60 characters)",
                "key_strengths": ["strength1", "strength2", "strength3"],
                "suggested_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=800
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Professional summary generation failed: {e}")
            
            # Fallback: Generate basic professional summary without AI
            fallback_summary = self._generate_fallback_summary(job_title, experience_years, key_skills, industry)
            
            return {
                "success": True,
                "data": fallback_summary,
                "fallback": True,
                "message": "AI services temporarily unavailable. Using template-based summary."
            }
    
    def enhance_work_experience(self, job_title: str, company: str, 
                               basic_description: str, achievements: List[str] = None) -> Dict[str, Any]:
        """
        AI-powered work experience enhancement
        Similar to Huntr's "Rewrite with AI" feature for bullet points
        """
        try:
            achievements_text = "\n".join([f"- {ach}" for ach in (achievements or [])])
            
            prompt = f"""
            Enhance this work experience entry for an ATS-optimized resume:
            
            Job Title: {job_title}
            Company: {company}
            Basic Description: {basic_description}
            Current Achievements: {achievements_text if achievements_text else "None provided"}
            
            Requirements:
            1. Create 4-6 compelling bullet points
            2. Start each bullet with strong action verbs
            3. Include quantifiable metrics where possible (use realistic estimates if not provided)
            4. Focus on impact and results, not just duties
            5. Use relevant industry keywords for ATS optimization
            6. Make achievements sound impressive but truthful
            7. Vary sentence structure and action verbs
            
            Also suggest relevant technologies and skills that should be highlighted.
            
            Respond with JSON:
            {{
                "enhanced_description": "2-3 sentence role overview",
                "bullet_points": ["Enhanced bullet point 1", "Enhanced bullet point 2", "..."],
                "suggested_technologies": ["tech1", "tech2", "tech3"],
                "action_verbs_used": ["verb1", "verb2", "verb3"],
                "impact_metrics": ["metric1", "metric2"],
                "keywords": ["keyword1", "keyword2", "keyword3"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Work experience enhancement failed: {e}")
            
            # Fallback: Basic enhancement without AI
            fallback_result = self._generate_fallback_experience_enhancement(title, company, description)
            
            return {
                "success": True,
                "data": fallback_result,
                "fallback": True,
                "message": "AI services temporarily unavailable. Using template-based enhancement."
            }
    
    def analyze_job_match(self, resume_data: Dict, job_description: str) -> Dict[str, Any]:
        """
        Analyze how well a resume matches a job description
        Similar to Huntr's job-tailored resume analysis
        """
        try:
            # Extract key resume information
            skills = resume_data.get('technical_skills', []) + resume_data.get('soft_skills', [])
            experience = resume_data.get('work_experiences', [])
            education = resume_data.get('education', [])
            
            resume_summary = f"""
            Professional Summary: {resume_data.get('professional_summary', '')}
            Skills: {', '.join(skills[:20])}
            Recent Experience: {experience[0].get('description', '') if experience else 'No experience listed'}
            Education: {education[0].get('degree_type', '') + ' in ' + education[0].get('field_of_study', '') if education else 'No education listed'}
            """
            
            prompt = f"""
            Analyze how well this resume matches the job description and provide optimization suggestions.
            
            RESUME SUMMARY:
            {resume_summary}
            
            JOB DESCRIPTION:
            {job_description}
            
            Provide a comprehensive analysis including:
            1. Overall match percentage (0-100%)
            2. Matching skills and keywords found
            3. Missing critical keywords and skills
            4. Specific suggestions to improve match score
            5. ATS optimization recommendations
            6. Content gaps that should be addressed
            
            Respond with JSON:
            {{
                "match_percentage": 85,
                "matching_skills": ["skill1", "skill2"],
                "missing_keywords": ["keyword1", "keyword2"],
                "missing_skills": ["skill1", "skill2"],
                "content_suggestions": ["suggestion1", "suggestion2"],
                "ats_recommendations": ["rec1", "rec2"],
                "priority_improvements": ["high priority item 1", "high priority item 2"],
                "strength_areas": ["area1", "area2"],
                "improvement_areas": ["area1", "area2"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1200
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Job match analysis failed: {e}")
            return {
                "success": False,
                "error": f"Failed to analyze job match: {str(e)}"
            }
    
    def generate_skills_suggestions(self, job_title: str, industry: str, 
                                  current_skills: List[str] = None) -> Dict[str, Any]:
        """
        Generate relevant skills suggestions based on job title and industry
        Similar to Huntr's skills generator
        """
        try:
            current_skills_text = ", ".join(current_skills or [])
            
            prompt = f"""
            Suggest relevant skills for a {job_title} position in the {industry} industry.
            
            Current skills: {current_skills_text or "None listed"}
            
            Provide suggestions in these categories:
            1. Technical/Hard Skills (most important for ATS)
            2. Software/Tools
            3. Soft Skills
            4. Industry-specific skills
            5. Trending/In-demand skills for this role
            
            Focus on skills that are:
            - Commonly requested in job descriptions
            - ATS-friendly keywords
            - Relevant to current market demands
            - Appropriate for the experience level
            
            Respond with JSON:
            {{
                "technical_skills": ["skill1", "skill2", "skill3"],
                "software_tools": ["tool1", "tool2", "tool3"],
                "soft_skills": ["skill1", "skill2", "skill3"],
                "industry_specific": ["skill1", "skill2", "skill3"],
                "trending_skills": ["skill1", "skill2", "skill3"],
                "priority_additions": ["Most important skill to add", "Second priority"],
                "skill_categories": {{"category1": ["skill1", "skill2"], "category2": ["skill3", "skill4"]}}
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.6,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Skills suggestions generation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to generate skills suggestions: {str(e)}"
            }
    
    def analyze_resume_ats_compatibility(self, resume_content: str) -> Dict[str, Any]:
        """
        Comprehensive ATS compatibility analysis
        Based on Microsoft ATS resume template guidelines
        """
        try:
            prompt = f"""
            Analyze this resume content for ATS (Applicant Tracking System) compatibility and provide optimization suggestions.
            
            RESUME CONTENT:
            {resume_content}
            
            Evaluate these areas (score 0-100 for each):
            1. ATS Compatibility - formatting, structure, parsability
            2. Keyword Optimization - industry keywords, job-relevant terms
            3. Content Quality - achievements, quantified results
            4. Format Structure - sections, headers, organization
            5. Length Optimization - appropriate length for experience level
            6. Professional Language - tone, clarity, action verbs
            
            Provide specific recommendations for improvement in each area.
            
            Respond with JSON:
            {{
                "overall_score": 85,
                "ats_compatibility": 90,
                "keyword_optimization": 75,
                "content_quality": 80,
                "format_structure": 95,
                "length_optimization": 85,
                "professional_language": 88,
                "strengths": ["strength1", "strength2", "strength3"],
                "critical_issues": ["issue1", "issue2"],
                "improvement_suggestions": ["suggestion1", "suggestion2", "suggestion3"],
                "keyword_recommendations": ["keyword1", "keyword2", "keyword3"],
                "ats_warnings": ["warning1", "warning2"],
                "format_recommendations": ["format tip 1", "format tip 2"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=1200
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"ATS compatibility analysis failed: {e}")
            return {
                "success": False,
                "error": f"Failed to analyze ATS compatibility: {str(e)}"
            }
    
    def generate_project_description(self, project_name: str, technologies: List[str], 
                                   basic_description: str = "") -> Dict[str, Any]:
        """
        Generate enhanced project descriptions for resumes
        """
        try:
            tech_list = ", ".join(technologies) if technologies else "various technologies"
            
            prompt = f"""
            Create an enhanced project description for a resume:
            
            Project Name: {project_name}
            Technologies Used: {tech_list}
            Basic Description: {basic_description or "No description provided"}
            
            Requirements:
            1. Create a compelling 2-3 sentence project overview
            2. Generate 3-4 bullet points highlighting key achievements
            3. Focus on technical skills demonstrated
            4. Include quantifiable results where possible
            5. Use action verbs and technical keywords
            6. Make it relevant for software/tech positions
            
            Respond with JSON:
            {{
                "enhanced_description": "2-3 sentence project overview",
                "achievement_bullets": ["bullet1", "bullet2", "bullet3", "bullet4"],
                "technical_highlights": ["tech skill 1", "tech skill 2", "tech skill 3"],
                "impact_statements": ["impact1", "impact2"],
                "suggested_keywords": ["keyword1", "keyword2", "keyword3"]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=800
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                "success": True,
                "data": result
            }
            
        except Exception as e:
            self.logger.error(f"Project description generation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to generate project description: {str(e)}"
            }


def create_resume_builder_ai():
    """Factory function to create Resume Builder AI instance"""
    return ResumeBuilderAI()


    def _generate_fallback_summary(self, job_title: str, experience_years: int, 
                                 key_skills: List[str], industry: str = "") -> Dict[str, Any]:
        """Generate fallback professional summary without AI"""
        
        # Create basic professional summary template
        exp_text = f"{experience_years} years" if experience_years > 1 else "1 year"
        skills_text = ", ".join(key_skills[:5]) if key_skills else "various technical skills"
        
        summary_templates = [
            f"Experienced {job_title} with {exp_text} of experience in {industry or 'technology'} industry. Skilled in {skills_text}. Proven track record of delivering high-quality solutions and contributing to team success.",
            f"Results-driven {job_title} with {exp_text} of professional experience. Expertise in {skills_text}. Strong problem-solving abilities and commitment to continuous learning and improvement.",
            f"Dedicated {job_title} professional with {exp_text} of experience. Proficient in {skills_text}. Focused on delivering efficient solutions and collaborating effectively with cross-functional teams."
        ]
        
        # Select template based on experience level
        if experience_years >= 5:
            template_idx = 0
        elif experience_years >= 2:
            template_idx = 1
        else:
            template_idx = 2
            
        return {
            "professional_summary": summary_templates[template_idx],
            "headline": f"{job_title} | {exp_text} Experience",
            "key_strengths": ["Problem Solving", "Team Collaboration", "Technical Excellence"],
            "suggested_keywords": key_skills[:5] if key_skills else ["Technical Skills", "Problem Solving", "Team Work"]
        }
    
    def _generate_fallback_experience_enhancement(self, title: str, company: str, description: str) -> Dict[str, Any]:
        """Generate fallback work experience enhancement without AI"""
        
        # Basic enhancement by adding action verbs and structure
        enhanced_desc = f"Worked as {title} at {company}. {description}"
        
        # Create basic bullet points from description
        sentences = description.split('. ')
        bullet_points = []
        
        for sentence in sentences[:3]:  # Limit to 3 bullet points
            if sentence.strip():
                # Add action verb if not present
                if not any(sentence.lower().startswith(verb) for verb in ['developed', 'implemented', 'managed', 'created', 'designed', 'led', 'built', 'improved']):
                    bullet_points.append(f"• Contributed to {sentence.strip()}")
                else:
                    bullet_points.append(f"• {sentence.strip()}")
        
        if not bullet_points:
            bullet_points = [f"• Performed {title} responsibilities at {company}"]
        
        return {
            "enhanced_description": enhanced_desc,
            "bullet_points": bullet_points,
            "suggested_technologies": ["Technology", "Tools", "Systems"],
            "action_verbs_used": ["Contributed", "Performed", "Worked"],
            "impact_metrics": ["Improved efficiency", "Enhanced performance"],
            "keywords": [title, company, "Professional"]
        }


# Quick test function

def test_resume_builder_ai():
    """Test function for the Resume Builder AI service"""
    try:
        ai = ResumeBuilderAI()
        
        # Test professional summary generation
        result = ai.generate_professional_summary(
            job_title="Software Engineer",
            experience_years=3,
            key_skills=["Python", "React", "Node.js", "PostgreSQL"],
            industry="Technology"
        )
        
        print("Professional Summary Test:")
        print(json.dumps(result, indent=2))
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    # Run test when script is executed directly
    test_resume_builder_ai()