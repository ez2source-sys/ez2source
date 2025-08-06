"""
Interview Feedback Summarizer Service for Job2Hire
Provides AI-powered analysis and summaries of interview responses
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
import os

from models import InterviewResponse, Interview, User, db

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class InterviewFeedbackSummarizer:
    """AI-powered interview feedback analysis and summarization"""
    
    def __init__(self):
        self.client = openai_client
        
    def generate_comprehensive_summary(self, interview_response: InterviewResponse) -> Dict:
        """Generate a comprehensive summary of an interview response"""
        try:
            # Get interview and candidate details
            interview = Interview.query.get(interview_response.interview_id)
            candidate = User.query.get(interview_response.candidate_id)
            
            if not interview or not candidate:
                raise ValueError("Interview or candidate not found")
            
            # Parse interview answers
            answers = json.loads(interview_response.answers) if interview_response.answers else {}
            
            # Create comprehensive prompt
            prompt = self._build_summary_prompt(interview, candidate, answers, interview_response)
            
            # Generate AI summary
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert HR analyst and interview assessor. Provide detailed, actionable feedback based on interview responses. Be professional, constructive, and specific."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            # Parse AI response
            ai_analysis = json.loads(response.choices[0].message.content)
            
            # Enhance with additional metrics
            summary = self._enhance_summary_with_metrics(ai_analysis, interview_response, answers)
            
            return summary
            
        except Exception as e:
            logging.error(f"Error generating interview summary: {e}")
            return self._get_fallback_summary(interview_response)
    
    def _build_summary_prompt(self, interview: Interview, candidate: User, answers: Dict, response: InterviewResponse) -> str:
        """Build comprehensive prompt for AI analysis"""
        
        # Format answers for analysis
        formatted_answers = "\n".join([
            f"Q{i+1}: {answer}" for i, answer in enumerate(answers.values())
        ])
        
        prompt = f"""
        Analyze this interview response and provide a comprehensive assessment in JSON format:

        INTERVIEW DETAILS:
        - Position: {interview.title}
        - Job Description: {interview.job_description[:500]}...
        - Interview Type: {interview.interview_type}
        
        CANDIDATE DETAILS:
        - Name: {candidate.first_name} {candidate.last_name}
        - Email: {candidate.email}
        - Time Taken: {response.time_taken_minutes} minutes
        - Current AI Score: {response.ai_score}/100
        
        INTERVIEW RESPONSES:
        {formatted_answers}
        
        Please provide analysis in this exact JSON format:
        {{
            "overall_summary": "Brief 2-3 sentence overview of candidate performance",
            "strengths": [
                "Specific strength 1 with examples",
                "Specific strength 2 with examples",
                "Specific strength 3 with examples"
            ],
            "areas_for_improvement": [
                "Specific area 1 with suggestions",
                "Specific area 2 with suggestions"
            ],
            "technical_competency": {{
                "score": 85,
                "assessment": "Detailed technical assessment",
                "key_skills_demonstrated": ["skill1", "skill2", "skill3"]
            }},
            "communication_skills": {{
                "score": 78,
                "assessment": "Communication style and clarity evaluation",
                "notable_points": ["point1", "point2"]
            }},
            "cultural_fit": {{
                "score": 82,
                "assessment": "How well candidate aligns with role expectations",
                "indicators": ["indicator1", "indicator2"]
            }},
            "recommended_next_steps": [
                "Specific recommendation 1",
                "Specific recommendation 2"
            ],
            "interview_quality_metrics": {{
                "response_depth": 85,
                "relevance_to_role": 88,
                "problem_solving_approach": 79
            }},
            "recruiter_notes": "Key talking points for recruiter follow-up",
            "hiring_recommendation": "Strong Hire|Hire|On the Fence|No Hire",
            "confidence_level": 85
        }}
        """
        
        return prompt
    
    def _enhance_summary_with_metrics(self, ai_analysis: Dict, response: InterviewResponse, answers: Dict) -> Dict:
        """Enhance AI summary with additional calculated metrics"""
        
        # Calculate response metrics
        total_words = sum(len(str(answer).split()) for answer in answers.values())
        avg_response_length = total_words / len(answers) if answers else 0
        
        # Add metadata
        ai_analysis["metadata"] = {
            "generated_at": datetime.utcnow().isoformat(),
            "response_id": response.id,
            "total_words": total_words,
            "average_response_length": round(avg_response_length, 1),
            "completion_time_minutes": response.time_taken_minutes,
            "original_ai_score": response.ai_score
        }
        
        # Calculate overall recommendation score
        scores = []
        if "technical_competency" in ai_analysis and "score" in ai_analysis["technical_competency"]:
            scores.append(ai_analysis["technical_competency"]["score"])
        if "communication_skills" in ai_analysis and "score" in ai_analysis["communication_skills"]:
            scores.append(ai_analysis["communication_skills"]["score"])
        if "cultural_fit" in ai_analysis and "score" in ai_analysis["cultural_fit"]:
            scores.append(ai_analysis["cultural_fit"]["score"])
            
        if scores:
            ai_analysis["overall_score"] = round(sum(scores) / len(scores), 1)
        
        return ai_analysis
    
    def _get_fallback_summary(self, response: InterviewResponse) -> Dict:
        """Provide fallback summary when AI analysis fails"""
        return {
            "overall_summary": "Interview response recorded successfully. AI analysis temporarily unavailable.",
            "strengths": ["Response submitted within time limit"],
            "areas_for_improvement": ["Detailed analysis pending"],
            "overall_score": response.ai_score or 0,
            "hiring_recommendation": "Pending Analysis",
            "recruiter_notes": "Please review responses manually or retry AI analysis.",
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "response_id": response.id,
                "fallback_mode": True
            }
        }
    
    def generate_batch_summaries(self, interview_id: int, organization_id: int) -> List[Dict]:
        """Generate summaries for all responses to a specific interview"""
        try:
            responses = InterviewResponse.query.filter_by(
                interview_id=interview_id,
                organization_id=organization_id
            ).all()
            
            summaries = []
            for response in responses:
                summary = self.generate_comprehensive_summary(response)
                summary["candidate_id"] = response.candidate_id
                summaries.append(summary)
            
            return summaries
            
        except Exception as e:
            logging.error(f"Error generating batch summaries: {e}")
            return []
    
    def compare_candidates(self, interview_id: int, organization_id: int) -> Dict:
        """Generate comparative analysis of all candidates for an interview"""
        try:
            summaries = self.generate_batch_summaries(interview_id, organization_id)
            
            if not summaries:
                return {"error": "No interview responses found"}
            
            # Build comparison prompt
            comparison_prompt = self._build_comparison_prompt(summaries, interview_id)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert hiring manager. Compare candidates objectively and provide actionable recommendations."
                    },
                    {
                        "role": "user",
                        "content": comparison_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            comparison = json.loads(response.choices[0].message.content)
            comparison["total_candidates"] = len(summaries)
            comparison["generated_at"] = datetime.utcnow().isoformat()
            
            return comparison
            
        except Exception as e:
            logging.error(f"Error generating candidate comparison: {e}")
            return {"error": "Comparison analysis failed"}
    
    def _build_comparison_prompt(self, summaries: List[Dict], interview_id: int) -> str:
        """Build prompt for candidate comparison analysis"""
        
        candidate_data = []
        for i, summary in enumerate(summaries, 1):
            candidate_info = f"""
            Candidate {i}:
            - Overall Score: {summary.get('overall_score', 'N/A')}
            - Hiring Recommendation: {summary.get('hiring_recommendation', 'N/A')}
            - Key Strengths: {', '.join(summary.get('strengths', [])[:2])}
            - Technical Score: {summary.get('technical_competency', {}).get('score', 'N/A')}
            - Communication Score: {summary.get('communication_skills', {}).get('score', 'N/A')}
            """
            candidate_data.append(candidate_info)
        
        prompt = f"""
        Compare these {len(summaries)} candidates who interviewed for the same position:
        
        {chr(10).join(candidate_data)}
        
        Provide analysis in this JSON format:
        {{
            "ranking": [
                {{
                    "candidate_number": 1,
                    "rationale": "Why this candidate ranks highest"
                }},
                {{
                    "candidate_number": 2,
                    "rationale": "Why this candidate ranks second"
                }}
            ],
            "top_performers": [
                {{
                    "candidate_number": 1,
                    "key_advantages": ["advantage1", "advantage2"]
                }}
            ],
            "hiring_recommendations": {{
                "immediate_hire": [1, 3],
                "second_round": [2],
                "decline": []
            }},
            "comparative_insights": [
                "Key insight about the candidate pool",
                "Notable patterns or trends"
            ],
            "decision_summary": "Executive summary for hiring decision"
        }}
        """
        
        return prompt

def get_interview_feedback_summary(response_id: int, user_id: int) -> Optional[Dict]:
    """Get comprehensive feedback summary for an interview response"""
    try:
        response = InterviewResponse.query.get(response_id)
        if not response:
            return None
        
        # Verify access permissions
        user = User.query.get(user_id)
        if not user:
            return None
            
        # Check if user has access to this response
        if user.role == 'candidate' and response.candidate_id != user_id:
            return None
        elif user.role == 'recruiter' and response.organization_id != user.organization_id:
            return None
        
        # Generate summary
        summarizer = InterviewFeedbackSummarizer()
        summary = summarizer.generate_comprehensive_summary(response)
        
        return summary
        
    except Exception as e:
        logging.error(f"Error getting feedback summary: {e}")
        return None

def get_interview_comparison(interview_id: int, user_id: int) -> Optional[Dict]:
    """Get comparative analysis of all candidates for an interview"""
    try:
        user = User.query.get(user_id)
        if not user or user.role != 'recruiter':
            return None
        
        interview = Interview.query.get(interview_id)
        if not interview or interview.recruiter_id != user_id:
            return None
        
        summarizer = InterviewFeedbackSummarizer()
        comparison = summarizer.compare_candidates(interview_id, user.organization_id)
        
        return comparison
        
    except Exception as e:
        logging.error(f"Error getting interview comparison: {e}")
        return None