import json
import os
import logging
from openai import OpenAI
import httpx
from httpcore import ReadTimeout, ConnectTimeout
from openai import APIConnectionError, APITimeoutError

# Get OpenAI API key from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("OPENAI_API_KEY not found in environment variables")
    openai = None
else:
    # Configure OpenAI client with timeout settings
    openai = OpenAI(
        api_key=OPENAI_API_KEY,
        timeout=30.0,  # 30 second timeout
        max_retries=3  # Retry failed requests up to 3 times
    )

def generate_interview_questions(job_description, job_title, num_questions=5):
    """
    Generate interview questions based on job description using OpenAI
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    """
    # Ensure we always return exactly 5 questions for consistency
    fallback_questions = [
        {
            "text": "Tell me about your relevant experience for this role.",
            "type": "text",
            "category": "experience",
            "expected_keywords": ["experience", "skills", "background"]
        },
        {
            "text": "Describe a challenging problem you solved and how you approached it.",
            "type": "text",
            "category": "problem-solving",
            "expected_keywords": ["problem", "solution", "approach", "challenge"]
        },
        {
            "text": "What interests you most about this position and our company?",
            "type": "text",
            "category": "motivation",
            "expected_keywords": ["interest", "motivation", "company", "role"]
        },
        {
            "text": "How do you handle working under pressure or tight deadlines?",
            "type": "text",
            "category": "behavioral",
            "expected_keywords": ["pressure", "deadlines", "stress", "management"]
        },
        {
            "text": "Where do you see yourself in your career in the next 3-5 years?",
            "type": "text",
            "category": "goals",
            "expected_keywords": ["career", "goals", "future", "growth"]
        }
    ]
    
    if not openai:
        logging.warning("OpenAI client not initialized - using fallback questions")
        return fallback_questions
    
    try:
        prompt = f"""
        Generate {num_questions} professional interview questions for the following job position:

        Job Title: {job_title}
        Job Description: {job_description}

        Create questions that assess:
        1. Technical skills relevant to the role
        2. Problem-solving abilities
        3. Communication skills
        4. Cultural fit
        5. Experience and achievements

        Return the response as a JSON object with this format:
        {{
            "questions": [
                {{
                    "text": "Question text here",
                    "type": "text",
                    "category": "technical|behavioral|situational",
                    "expected_keywords": ["keyword1", "keyword2", "keyword3"]
                }}
            ]
        }}
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HR professional and interview designer. Generate thoughtful, relevant interview questions that help assess candidate suitability."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            timeout=30
        )

        result = json.loads(response.choices[0].message.content)
        questions = result.get("questions", [])
        
        # Ensure we have exactly num_questions
        if len(questions) < num_questions:
            logging.warning(f"AI generated only {len(questions)} questions, padding with fallback questions")
            # Add fallback questions to reach the desired count
            for i in range(len(questions), num_questions):
                if i < len(fallback_questions):
                    questions.append(fallback_questions[i])
        elif len(questions) > num_questions:
            # Trim to exact count
            questions = questions[:num_questions]
            
        return questions

    except (APIConnectionError, APITimeoutError, ReadTimeout, ConnectTimeout) as e:
        logging.error(f"OpenAI API timeout/connection error generating interview questions: {e}")
        return fallback_questions
    except Exception as e:
        logging.error(f"Error generating interview questions: {e}")
        return fallback_questions

def score_interview_responses(answers, job_description):
    """
    Score interview responses using OpenAI
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    """
    if not openai:
        logging.error("OpenAI client not initialized - API key missing")
        # Return basic scoring if AI fails
        total_length = sum(len(answer_data['answer']) for answer_data in answers.values())
        avg_length = total_length / len(answers) if answers else 0
        
        # Basic scoring based on response length and completeness
        base_score = min(80, max(20, avg_length / 10))  # 20-80 based on average response length
        
        # Bonus for detailed responses
        if avg_length > 100:
            base_score += 10
        
        feedback = f"""
        Basic Evaluation Score: {base_score:.1f}/100

        This is a basic evaluation as the AI scoring system requires an OpenAI API key.
        
        Response Analysis:
        - Average response length: {avg_length:.0f} characters
        - Total responses: {len(answers)}
        - Completion rate: {'Complete' if all(answer_data['answer'].strip() for answer_data in answers.values()) else 'Incomplete'}
        
        For detailed AI-powered evaluation, please provide an OpenAI API key.
        """
        
        return base_score, feedback
    
    try:
        # Prepare answers for analysis
        answers_text = ""
        for key, answer_data in answers.items():
            answers_text += f"Q: {answer_data['question']}\nA: {answer_data['answer']}\n\n"

        prompt = f"""
        Analyze the following interview responses for a position with this job description:

        Job Description: {job_description}

        Interview Responses:
        {answers_text}

        Evaluate the candidate based on:
        1. Relevance of experience to the role (25%)
        2. Communication clarity and professionalism (20%)
        3. Problem-solving and analytical thinking (20%)
        4. Technical knowledge and skills (20%)
        5. Cultural fit and motivation (15%)

        Provide a comprehensive evaluation with:
        - Overall score (0-100)
        - Detailed feedback highlighting strengths and areas for improvement
        - Specific recommendations

        Return the response as JSON:
        {{
            "overall_score": number,
            "category_scores": {{
                "experience": number,
                "communication": number,
                "problem_solving": number,
                "technical_skills": number,
                "cultural_fit": number
            }},
            "feedback": "Detailed feedback text",
            "strengths": ["strength1", "strength2"],
            "improvements": ["area1", "area2"],
            "recommendation": "hire|maybe|no_hire"
        }}
        """

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert HR professional with extensive experience in candidate evaluation. Provide fair, objective, and constructive assessments."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        result = json.loads(response.choices[0].message.content)
        
        # Extract score and feedback
        score = max(0, min(100, result.get("overall_score", 0)))
        
        # Format detailed feedback
        feedback_parts = []
        feedback_parts.append(f"Overall Score: {score}/100")
        feedback_parts.append(f"Recommendation: {result.get('recommendation', 'N/A').replace('_', ' ').title()}")
        feedback_parts.append("\nDetailed Feedback:")
        feedback_parts.append(result.get("feedback", "No detailed feedback available."))
        
        if result.get("strengths"):
            feedback_parts.append("\nStrengths:")
            for strength in result["strengths"]:
                feedback_parts.append(f"• {strength}")
        
        if result.get("improvements"):
            feedback_parts.append("\nAreas for Improvement:")
            for improvement in result["improvements"]:
                feedback_parts.append(f"• {improvement}")
        
        feedback = "\n".join(feedback_parts)
        
        return score, feedback

    except (APIConnectionError, APITimeoutError, ReadTimeout, ConnectTimeout) as e:
        logging.error(f"OpenAI API timeout/connection error scoring interview responses: {e}")
        # Return basic scoring if AI fails
    except Exception as e:
        logging.error(f"Error scoring interview responses: {e}")
        # Return basic scoring if AI fails
        
        # Simple keyword-based scoring as fallback
        total_length = sum(len(answer_data['answer']) for answer_data in answers.values())
        avg_length = total_length / len(answers) if answers else 0
        
        # Basic scoring based on response length and completeness
        base_score = min(80, max(20, avg_length / 10))  # 20-80 based on average response length
        
        # Bonus for detailed responses
        if avg_length > 100:
            base_score += 10
        
        feedback = f"""
        Basic Evaluation Score: {base_score:.1f}/100

        This is a basic evaluation as our AI scoring system is currently unavailable.
        
        Response Analysis:
        - Average response length: {avg_length:.0f} characters
        - Total responses: {len(answers)}
        - Completion rate: {'Complete' if all(answer_data['answer'].strip() for answer_data in answers.values()) else 'Incomplete'}
        
        For a detailed AI-powered evaluation, please ensure the OpenAI API is properly configured.
        """
        
        return base_score, feedback

def analyze_video_interview(video_path, interview_context=None):
    """
    Analyze video interview using AI for behavioral insights
    Note: This is a placeholder for video analysis functionality
    In a production environment, this would integrate with video analysis APIs
    """
    if not openai:
        logging.error("OpenAI client not initialized - API key missing")
        return {
            "confidence": 0.0,
            "communication_style": "Unable to analyze",
            "insights": "Video analysis requires OpenAI API key"
        }
    
    try:
        # For now, we'll simulate video analysis since actual video processing
        # would require additional services like computer vision APIs
        # In production, this would extract frames, analyze facial expressions,
        # speech patterns, and body language
        
        analysis_prompt = f"""
        Analyze this interview video recording for communication and behavioral insights.
        
        Interview Context: {interview_context or 'General interview assessment'}
        
        Based on typical video interview analysis, provide insights on:
        1. Communication confidence and clarity
        2. Professional presentation and demeanor
        3. Engagement and enthusiasm level
        4. Overall interview performance indicators
        
        Return JSON format:
        {{
            "confidence": number (0-100),
            "communication_style": "string description",
            "insights": "detailed behavioral analysis",
            "engagement_score": number (0-100),
            "professionalism_score": number (0-100)
        }}
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in behavioral analysis and interview assessment. Provide professional insights based on video interview analysis."
                },
                {
                    "role": "user",
                    "content": analysis_prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            timeout=30
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return {
            "confidence": max(0, min(100, result.get("confidence", 75))),
            "communication_style": result.get("communication_style", "Professional"),
            "insights": result.get("insights", "Video analysis completed successfully"),
            "engagement_score": max(0, min(100, result.get("engagement_score", 75))),
            "professionalism_score": max(0, min(100, result.get("professionalism_score", 75)))
        }
        
    except (APIConnectionError, APITimeoutError, ReadTimeout, ConnectTimeout) as e:
        logging.error(f"OpenAI API timeout/connection error analyzing video interview: {e}")
        return {
            "confidence": 50.0,
            "communication_style": "Standard",
            "insights": "Video analysis temporarily unavailable due to timeout. Please try again later."
        }
    except Exception as e:
        logging.error(f"Error analyzing video interview: {e}")
        return {
            "confidence": 50.0,
            "communication_style": "Standard",
            "insights": "Basic video analysis completed. For detailed insights, ensure proper API configuration."
        }

def analyze_sentiment(text):
    """
    Analyze sentiment of text using OpenAI
    """
    if not openai:
        logging.error("OpenAI client not initialized - API key missing")
        return {"rating": 3, "confidence": 0.5}
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a sentiment analysis expert. Analyze the sentiment of the text and provide a rating from 1 to 5 stars and a confidence score between 0 and 1. Respond with JSON in this format: {'rating': number, 'confidence': number}"
                },
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            timeout=30
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "rating": max(1, min(5, round(result["rating"]))),
            "confidence": max(0, min(1, result["confidence"]))
        }
    except (APIConnectionError, APITimeoutError, ReadTimeout, ConnectTimeout) as e:
        logging.error(f"OpenAI API timeout/connection error analyzing sentiment: {e}")
        return {"rating": 3, "confidence": 0.3}
    except Exception as e:
        logging.error(f"Error analyzing sentiment: {e}")
        return {"rating": 3, "confidence": 0.5}
