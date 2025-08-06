"""
Cover Letter Generation Service
AI-powered cover letter generation with company-specific templates
"""

import os
import json
import logging
from openai import OpenAI
from typing import Dict, List, Optional, Tuple

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

class CoverLetterGenerator:
    """AI-powered cover letter generator with company-specific templates"""
    
    def __init__(self):
        self.company_templates = {
            'google': {
                'name': 'Google',
                'culture': 'Innovation, data-driven decisions, technical excellence',
                'values': 'Don\'t be evil, user focus, think big',
                'focus_areas': ['technical innovation', 'scale impact', 'data-driven approach', 'user experience'],
                'keywords': ['innovation', 'scale', 'impact', 'technology', 'users', 'data', 'collaboration']
            },
            'amazon': {
                'name': 'Amazon',
                'culture': 'Customer obsession, ownership, high standards',
                'values': 'Customer obsession, ownership, invent and simplify, bias for action',
                'focus_areas': ['customer obsession', 'ownership', 'results delivery', 'innovation'],
                'keywords': ['customer obsession', 'ownership', 'deliver results', 'think big', 'dive deep']
            },
            'tesla': {
                'name': 'Tesla',
                'culture': 'Sustainable energy, innovation, fast-paced environment',
                'values': 'Sustainable future, innovation, excellence, speed',
                'focus_areas': ['sustainable energy', 'innovation', 'manufacturing excellence', 'mission-driven'],
                'keywords': ['sustainable', 'innovation', 'excellence', 'mission', 'future', 'technology']
            },
            'meta': {
                'name': 'Meta',
                'culture': 'Connect people, move fast, build social technology',
                'values': 'Move fast, be bold, focus on impact, be open',
                'focus_areas': ['social connection', 'global impact', 'technology innovation', 'community building'],
                'keywords': ['connect', 'community', 'impact', 'innovation', 'global', 'social', 'technology']
            },
            'microsoft': {
                'name': 'Microsoft',
                'culture': 'Empower every person and organization, inclusive, growth mindset',
                'values': 'Respect, integrity, accountability, inclusive',
                'focus_areas': ['empowerment', 'productivity', 'cloud technology', 'accessibility'],
                'keywords': ['empower', 'productivity', 'cloud', 'collaboration', 'accessibility', 'innovation']
            }
        }
        
        self.role_templates = {
            'frontend_developer': {
                'name': 'Frontend Developer',
                'key_skills': ['React', 'JavaScript', 'CSS', 'HTML', 'Vue.js', 'Angular'],
                'focus_areas': ['user experience', 'responsive design', 'performance optimization', 'accessibility'],
                'responsibilities': ['UI development', 'cross-browser compatibility', 'performance optimization']
            },
            'backend_developer': {
                'name': 'Backend Developer',
                'key_skills': ['Python', 'Java', 'Node.js', 'databases', 'APIs', 'cloud platforms'],
                'focus_areas': ['system architecture', 'scalability', 'data management', 'API design'],
                'responsibilities': ['server-side development', 'database design', 'API development']
            },
            'product_manager': {
                'name': 'Product Manager',
                'key_skills': ['product strategy', 'user research', 'data analysis', 'project management'],
                'focus_areas': ['product vision', 'user needs', 'market analysis', 'stakeholder management'],
                'responsibilities': ['product roadmap', 'requirements gathering', 'cross-functional collaboration']
            },
            'data_scientist': {
                'name': 'Data Scientist',
                'key_skills': ['Python', 'R', 'machine learning', 'statistics', 'SQL', 'data visualization'],
                'focus_areas': ['data analysis', 'machine learning', 'statistical modeling', 'insights generation'],
                'responsibilities': ['data analysis', 'model building', 'business insights']
            },
            'devops_engineer': {
                'name': 'DevOps Engineer',
                'key_skills': ['CI/CD', 'Docker', 'Kubernetes', 'AWS', 'automation', 'monitoring'],
                'focus_areas': ['infrastructure automation', 'deployment pipelines', 'system reliability'],
                'responsibilities': ['infrastructure management', 'deployment automation', 'monitoring']
            }
        }

    def generate_cover_letter(self, 
                            candidate_info: Dict,
                            job_details: Dict,
                            template_type: str = 'custom',
                            tone: str = 'professional') -> Dict:
        """
        Generate a personalized cover letter using AI
        
        Args:
            candidate_info: Dictionary with candidate details (name, skills, experience, etc.)
            job_details: Dictionary with job details (company, position, requirements, etc.)
            template_type: Type of template ('google', 'amazon', 'tesla', 'frontend_developer', etc.)
            tone: Tone of the letter ('professional', 'enthusiastic', 'technical')
        
        Returns:
            Dictionary with generated cover letter and metadata
        """
        if not openai_client:
            return self._fallback_template_generation(candidate_info, job_details, template_type)
        
        try:
            # Get template-specific guidance
            template_guidance = self._get_template_guidance(template_type)
            
            # Build the AI prompt
            prompt = self._build_generation_prompt(candidate_info, job_details, template_guidance, tone)
            
            # Generate cover letter using OpenAI
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert career counselor and professional writer specializing in creating compelling cover letters. Generate personalized, engaging cover letters that highlight relevant experience and demonstrate genuine interest in the role and company."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=1500,
                temperature=0.7
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return {
                'content': result.get('cover_letter', ''),
                'title': result.get('title', f"Cover Letter - {job_details.get('company', 'Position')}"),
                'key_points': result.get('key_points', []),
                'suggestions': result.get('suggestions', []),
                'template_type': template_type,
                'generated_by_ai': True,
                'generation_model': 'gpt-4o',
                'ai_prompt': prompt
            }
            
        except Exception as e:
            logging.error(f"Error generating cover letter with AI: {str(e)}")
            return self._fallback_template_generation(candidate_info, job_details, template_type)

    def _get_template_guidance(self, template_type: str) -> Dict:
        """Get specific guidance for the template type"""
        if template_type in self.company_templates:
            return {
                'type': 'company',
                'data': self.company_templates[template_type]
            }
        elif template_type in self.role_templates:
            return {
                'type': 'role',
                'data': self.role_templates[template_type]
            }
        else:
            return {
                'type': 'general',
                'data': {
                    'focus_areas': ['relevant experience', 'skills alignment', 'company interest'],
                    'keywords': ['experience', 'skills', 'contribution', 'growth', 'opportunity']
                }
            }

    def _build_generation_prompt(self, candidate_info: Dict, job_details: Dict, 
                               template_guidance: Dict, tone: str) -> str:
        """Build the AI generation prompt"""
        
        # Extract candidate information
        name = candidate_info.get('name', 'Candidate')
        experience = candidate_info.get('experience', [])
        skills = candidate_info.get('skills', [])
        education = candidate_info.get('education', [])
        
        # Extract job information
        company = job_details.get('company', 'Company')
        position = job_details.get('position', 'Position')
        requirements = job_details.get('requirements', '')
        job_description = job_details.get('description', '')
        
        # Build prompt based on template guidance
        guidance_text = ""
        if template_guidance['type'] == 'company':
            data = template_guidance['data']
            guidance_text = f"""
Company-Specific Guidelines for {data['name']}:
- Culture: {data['culture']}
- Values: {data['values']}
- Focus on: {', '.join(data['focus_areas'])}
- Key words to incorporate: {', '.join(data['keywords'])}
"""
        elif template_guidance['type'] == 'role':
            data = template_guidance['data']
            guidance_text = f"""
Role-Specific Guidelines for {data['name']}:
- Key skills to highlight: {', '.join(data['key_skills'])}
- Focus areas: {', '.join(data['focus_areas'])}
- Typical responsibilities: {', '.join(data['responsibilities'])}
"""
        
        prompt = f"""
Generate a compelling cover letter with the following information:

CANDIDATE INFORMATION:
- Name: {name}
- Skills: {', '.join(skills) if isinstance(skills, list) else skills}
- Experience: {json.dumps(experience) if experience else 'Not provided'}
- Education: {json.dumps(education) if education else 'Not provided'}

JOB INFORMATION:
- Company: {company}
- Position: {position}
- Requirements: {requirements}
- Job Description: {job_description}

{guidance_text}

TONE: {tone}

REQUIREMENTS:
1. Create a personalized, engaging cover letter that demonstrates genuine interest
2. Highlight relevant experience and skills that match the job requirements
3. Show knowledge of the company and role
4. Keep it concise (3-4 paragraphs)
5. Include specific examples when possible
6. Use the specified tone throughout

RESPONSE FORMAT (JSON):
{{
    "cover_letter": "The complete cover letter text",
    "title": "Suggested title for the cover letter",
    "key_points": ["List", "of", "key", "strengths", "highlighted"],
    "suggestions": ["List", "of", "suggestions", "for", "improvement"]
}}
"""
        
        return prompt

    def _fallback_template_generation(self, candidate_info: Dict, job_details: Dict, 
                                    template_type: str) -> Dict:
        """Fallback template-based generation when AI is not available"""
        
        name = candidate_info.get('name', 'Candidate')
        company = job_details.get('company', 'Company')
        position = job_details.get('position', 'Position')
        
        # Get template guidance
        template_guidance = self._get_template_guidance(template_type)
        
        # Create basic template
        if template_type in self.company_templates:
            template_data = self.company_templates[template_type]
            cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {position} position at {template_data['name']}. Your company's commitment to {template_data['culture']} aligns perfectly with my professional values and career aspirations.

In my previous experience, I have developed skills that directly relate to {template_data['name']}'s focus on {', '.join(template_data['focus_areas'][:2])}. I am particularly drawn to your company's mission and would welcome the opportunity to contribute to your team's continued success.

I am excited about the possibility of bringing my experience to {template_data['name']} and would appreciate the opportunity to discuss how my background can contribute to your team's goals.

Thank you for considering my application. I look forward to hearing from you.

Sincerely,
{name}"""
        else:
            # Generic template
            cover_letter = f"""Dear Hiring Manager,

I am writing to express my interest in the {position} position at {company}. Your company's reputation and the opportunity to contribute to your team's success strongly appeal to me.

My background and experience have prepared me well for this role, and I am confident that my skills would be valuable to your organization. I am particularly excited about the opportunity to grow and contribute in this position.

I would welcome the opportunity to discuss how my experience and enthusiasm can benefit your team. Thank you for considering my application.

Sincerely,
{name}"""
        
        return {
            'content': cover_letter,
            'title': f"Cover Letter - {company}",
            'key_points': ['Relevant experience', 'Company alignment', 'Growth opportunity'],
            'suggestions': ['Customize with specific examples', 'Research company values', 'Add quantifiable achievements'],
            'template_type': template_type,
            'generated_by_ai': False,
            'generation_model': 'template',
            'ai_prompt': None
        }

    def get_available_templates(self) -> Dict:
        """Get list of available templates with descriptions"""
        templates = {}
        
        # Company templates
        for key, data in self.company_templates.items():
            templates[key] = {
                'name': data['name'],
                'type': 'company',
                'description': f"Optimized for {data['name']} culture and values",
                'focus': data['focus_areas'][:3],
                'category': 'Company-Specific'
            }
        
        # Role templates
        for key, data in self.role_templates.items():
            templates[key] = {
                'name': data['name'],
                'type': 'role',
                'description': f"Tailored for {data['name']} positions",
                'focus': data['focus_areas'][:3],
                'category': 'Role-Specific'
            }
        
        return templates

    def analyze_cover_letter(self, cover_letter_text: str, job_requirements: str = "") -> Dict:
        """
        Analyze a cover letter and provide feedback
        
        Args:
            cover_letter_text: The cover letter content to analyze
            job_requirements: Optional job requirements to check alignment
        
        Returns:
            Dictionary with analysis results and suggestions
        """
        if not openai_client:
            return self._basic_cover_letter_analysis(cover_letter_text)
        
        try:
            prompt = f"""
Analyze the following cover letter and provide detailed feedback:

COVER LETTER:
{cover_letter_text}

JOB REQUIREMENTS (if provided):
{job_requirements}

Please analyze the cover letter for:
1. Overall effectiveness and impact
2. Structure and organization
3. Tone and professionalism
4. Specific examples and achievements
5. Alignment with job requirements (if provided)
6. Areas for improvement

Provide a score (1-100) and specific suggestions for improvement.

RESPONSE FORMAT (JSON):
{{
    "overall_score": 85,
    "strengths": ["List", "of", "identified", "strengths"],
    "weaknesses": ["List", "of", "areas", "for", "improvement"],
    "suggestions": ["Specific", "improvement", "suggestions"],
    "alignment_score": 80,
    "missing_elements": ["Elements", "that", "could", "be", "added"],
    "tone_assessment": "Professional and engaging",
    "structure_feedback": "Well-organized with clear flow"
}}
"""
            
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert career counselor and hiring manager. Analyze cover letters professionally and provide constructive feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=800,
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logging.error(f"Error analyzing cover letter: {str(e)}")
            return self._basic_cover_letter_analysis(cover_letter_text)

    def _basic_cover_letter_analysis(self, cover_letter_text: str) -> Dict:
        """Basic analysis when AI is not available"""
        word_count = len(cover_letter_text.split())
        
        # Basic checks
        has_greeting = any(greeting in cover_letter_text.lower() for greeting in ['dear', 'hello', 'hi'])
        has_closing = any(closing in cover_letter_text.lower() for closing in ['sincerely', 'regards', 'thank you'])
        
        score = 60  # Base score
        if has_greeting: score += 10
        if has_closing: score += 10
        if 200 <= word_count <= 400: score += 15
        if word_count > 100: score += 5
        
        return {
            'overall_score': min(score, 95),
            'strengths': ['Appropriate length' if 200 <= word_count <= 400 else 'Content provided'],
            'weaknesses': ['Consider AI analysis for detailed feedback'],
            'suggestions': ['Use AI-powered analysis for comprehensive feedback'],
            'alignment_score': 70,
            'missing_elements': ['Requires detailed analysis'],
            'tone_assessment': 'Unable to assess without AI',
            'structure_feedback': f'Word count: {word_count} words'
        }

def get_cover_letter_examples() -> Dict:
    """Get example cover letters for different scenarios"""
    return {
        'google_software_engineer': {
            'title': 'Google Software Engineer',
            'company': 'Google',
            'position': 'Software Engineer',
            'content': '''Dear Hiring Manager,

I am writing to express my strong interest in the Software Engineer position at Google. Your company's commitment to innovation and creating technology that organizes the world's information perfectly aligns with my passion for developing scalable solutions that impact millions of users.

In my previous role at a fintech startup, I led the development of a real-time payment processing system that handled over 10,000 transactions per minute, directly contributing to a 40% increase in user engagement. This experience taught me the importance of building robust, scalable systems – a core principle I know Google values deeply. I am particularly excited about Google's approach to solving complex technical challenges through data-driven innovation and would welcome the opportunity to contribute to projects that operate at such massive scale.

My expertise in distributed systems, machine learning, and cloud architecture, combined with my experience in agile development environments, would enable me to make meaningful contributions to your engineering teams from day one. I am especially drawn to Google's culture of encouraging bold ideas and technical excellence.

Thank you for considering my application. I would be thrilled to discuss how my passion for innovation and technical expertise can contribute to Google's mission of organizing the world's information and making it universally accessible.

Sincerely,
[Your Name]''',
            'key_features': ['Scale emphasis', 'Data-driven approach', 'Innovation focus', 'Quantified achievements']
        },
        'amazon_product_manager': {
            'title': 'Amazon Product Manager',
            'company': 'Amazon',
            'position': 'Product Manager',
            'content': '''Dear Hiring Manager,

I am excited to apply for the Product Manager position at Amazon. Your company's relentless focus on customer obsession and commitment to delivering exceptional value resonates deeply with my product management philosophy and career aspirations.

Throughout my career, I have consistently demonstrated Amazon's core principle of working backwards from customer needs. At my previous company, I led the development of a customer feedback platform that reduced response time by 60% and increased customer satisfaction scores by 35%. This experience reinforced my belief that the best products start with a deep understanding of customer pain points – a principle that drives every aspect of Amazon's product development process.

My track record of delivering results in fast-paced environments aligns well with Amazon's bias for action. I successfully launched three major product features ahead of schedule, each exceeding adoption targets by at least 25%. I thrive in environments where ownership and high standards are not just expected but celebrated, and I am eager to bring this mindset to Amazon's dynamic product teams.

I am particularly excited about the opportunity to work on products that serve millions of customers worldwide and would welcome the chance to discuss how my customer-centric approach and proven ability to deliver results can contribute to Amazon's continued growth and innovation.

Sincerely,
[Your Name]''',
            'key_features': ['Customer obsession', 'Results delivery', 'Ownership mentality', 'Scale impact']
        },
        'tesla_engineer': {
            'title': 'Tesla Engineer',
            'company': 'Tesla',
            'position': 'Engineer',
            'content': '''Dear Hiring Manager,

I am writing to express my passionate interest in the Engineer position at Tesla. Your company's mission to accelerate the world's transition to sustainable energy represents exactly the kind of meaningful work I want to dedicate my career to pursuing.

My engineering background in battery technology and renewable energy systems has prepared me well for Tesla's fast-paced, innovation-driven environment. At my current position, I developed a battery optimization algorithm that improved energy efficiency by 18%, directly contributing to extending vehicle range – work that I believe would translate well to Tesla's cutting-edge electric vehicle technology. I am particularly drawn to Tesla's approach of vertical integration and manufacturing excellence.

What excites me most about Tesla is the company's commitment to pushing boundaries and challenging conventional thinking. I thrive in environments where innovation is not just encouraged but essential, and where engineering decisions directly impact our planet's future. My experience with rapid prototyping and iterative design aligns perfectly with Tesla's culture of continuous improvement and speed to market.

I am eager to contribute to Tesla's mission of creating a sustainable future and would welcome the opportunity to discuss how my technical expertise and passion for sustainable technology can help accelerate your innovative projects.

Sincerely,
[Your Name]''',
            'key_features': ['Mission alignment', 'Innovation focus', 'Sustainability passion', 'Technical excellence']
        }
    }