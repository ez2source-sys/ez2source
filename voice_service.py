"""
Voice Dictation Service for Job2Hire
Handles audio transcription using OpenAI Whisper API
"""

import os
import logging
import tempfile
from openai import OpenAI

# Initialize OpenAI client - handle missing API key gracefully
try:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
    else:
        client = None
        logging.warning("OPENAI_API_KEY not found in environment variables")
except Exception as e:
    client = None
    logging.error(f"Failed to initialize OpenAI client: {e}")

def transcribe_audio(audio_file):
    """
    Transcribe audio file using OpenAI Whisper
    
    Args:
        audio_file: File-like object containing audio data
        
    Returns:
        dict: Transcription result with success status and transcript text
    """
    if client is None:
        return {
            'success': False,
            'error': 'OpenAI API key not configured. Voice transcription is unavailable.',
            'transcript': ''
        }
    
    try:
        # Save audio data to temporary file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
            audio_file.seek(0)
            temp_file.write(audio_file.read())
            temp_file_path = temp_file.name
        
        # Transcribe using OpenAI Whisper
        with open(temp_file_path, 'rb') as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                response_format="text"
            )
        
        # Clean up temporary file
        os.unlink(temp_file_path)
        
        # Return successful result
        return {
            'success': True,
            'transcript': transcript.strip(),
            'error': None
        }
        
    except Exception as e:
        logging.error(f"Audio transcription error: {e}")
        
        # Clean up temporary file if it exists
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
        except:
            pass
        
        return {
            'success': False,
            'transcript': None,
            'error': str(e)
        }

def validate_audio_file(audio_file):
    """
    Validate audio file before processing
    
    Args:
        audio_file: File-like object to validate
        
    Returns:
        dict: Validation result
    """
    try:
        # Check file size (max 25MB for Whisper)
        audio_file.seek(0, 2)  # Seek to end
        file_size = audio_file.tell()
        audio_file.seek(0)  # Reset to beginning
        
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            return {
                'valid': False,
                'error': f'Audio file too large. Maximum size is 25MB, got {file_size / (1024*1024):.1f}MB'
            }
        
        if file_size == 0:
            return {
                'valid': False,
                'error': 'Audio file is empty'
            }
        
        return {
            'valid': True,
            'error': None
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'File validation error: {str(e)}'
        }