"""
AI Service Module
Provides AI essay correction and analysis functions
"""

import requests
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
import os

from config.ai_config import AI_CONFIG, SCORING_RULES, ERROR_TYPES

# Get logger
logger = logging.getLogger(__name__)

class AIService:
    """AI Service class for essay correction functions"""
    
    def __init__(self, config=None):
        """Initialize AI service
        
        Args:
            config: AI configuration, default uses AI_CONFIG
        """
        self.config = config or AI_CONFIG
        self.api_key = self.config['API_KEY']
        self.base_url = self.config['BASE_URL']
        self.model = self.config['MODEL']
        self.timeout = self.config['TIMEOUT']
    
    def correct_essay(self, essay_text: str, title: str = None, grade: str = None) -> Dict:
        """Correct an essay
        
        Args:
            essay_text: Essay content
            title: Essay title
            grade: Grade level (e.g. high school, junior high)
            
        Returns:
            Dict: Correction results
        """
        start_time = time.time()
        logger.info(f"Starting essay correction: {title or 'No title'}")
        
        # Construct correction system prompt
        system_prompt = self.config['CORRECTION_SYSTEM_PROMPT']
        
        if grade:
            system_prompt += f"\nPlease correct according to {grade} level standards."
        
        # Construct correction user prompt
        user_prompt = f"""Please help me correct the following essay and return results in JSON format.

Essay title: {title or "No title"}

Essay content:
{essay_text}

Please return the correction results in the following JSON format:
{{
    "score": {{
        "total": 90,  // Total score (out of 100)
        "content": 90,  // Content score (out of 100)
        "language": 90,  // Language score (out of 100)
        "structure": 90,  // Structure score (out of 100)
        "writing": 90  // Writing score (out of 100)
    }},
    "feedback": {{
        "overall": "Overall evaluation...",
        "content": "Content evaluation...",
        "language": "Language evaluation...",
        "structure": "Structure evaluation...",
        "writing": "Writing evaluation..."
    }},
    "errors": [
        {{
            "type": "error type",  // e.g. grammar, spelling, etc.
            "original": "original text",
            "correction": "correction",
            "explanation": "explanation"
        }}
    ],
    "improvement_suggestions": [
        "Improvement suggestion 1",
        "Improvement suggestion 2"
    ],
    "corrected_text": "[Complete corrected text]",
    "word_count": 250  // Word count
}}

Note: 
1. Output in JSON format only
2. Please provide detailed explanations based on actual issues
3. Error types can be chosen from: grammar, spelling, punctuation, word_choice, verb_tense, subject_verb_agreement, article, preposition, pronoun, word_order, redundancy, missing_word, collocation
4. Scoring guidelines: 90-100 (excellent), 80-89 (good), 70-79 (average), 60-69 (passing), 0-59 (failing)
5. Only output pure JSON content without quotes or placeholders"""

        try:
            # Call AI API
            response = self._call_ai_api(system_prompt, user_prompt)
            process_time = time.time() - start_time
            logger.info(f"AI API call completed, time taken: {process_time:.2f}s")
            
            # Parse results
            result = self._parse_correction_result(response, essay_text)
            result['success'] = True
            result['process_time'] = process_time
            
            return result
            
        except Exception as e:
            logger.error(f"Essay correction failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def _call_ai_api(self, system_prompt: str, user_prompt: str) -> str:
        """Call AI API
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            
        Returns:
            str: API response text
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Prepare request data
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.config.get('TEMPERATURE', 0.2),
            "max_tokens": self.config.get('MAX_TOKENS', 4000)
        }
        
        try:
            # Send request
            response = requests.post(
                f"{self.base_url}/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=self.timeout
            )
            
            # Check response status
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Extract generated text
            completion_text = data['choices'][0]['message']['content']
            return completion_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API request failed: {str(e)}")
            raise Exception(f"AI service request failed: {str(e)}")
    
    def _parse_correction_result(self, response_text: str, original_text: str) -> Dict:
        """Parse correction results
        
        Args:
            response_text: API response text
            original_text: Original essay content
            
        Returns:
            Dict: Parsed correction results
        """
        try:
            # Try to parse JSON directly
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON part
                json_match = response_text.strip()
                if json_match.startswith('```json'):
                    json_match = json_match.replace('```json', '').replace('```', '')
                elif json_match.startswith('```'):
                    json_match = json_match.replace('```', '')
                
                result = json.loads(json_match.strip())
            
            # Ensure results include all required fields
            if not isinstance(result, dict):
                raise ValueError("Parsed result is not a valid dictionary")
                
            # Add word count (if API didn't return it)
            if 'word_count' not in result:
                result['word_count'] = len(original_text)
                
            # Ensure scores are integers
            if 'score' in result:
                for key, value in result['score'].items():
                    if isinstance(value, str):
                        try:
                            result['score'][key] = int(value)
                        except ValueError:
                            result['score'][key] = 0
            
            # Return processed results
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse correction results: {str(e)}", exc_info=True)
            raise Exception(f"Failed to parse correction results: {str(e)}")
    
    def analyze_essay(self, essay_text: str, title: str = None) -> Dict:
        """Analyze essay content
        
        Args:
            essay_text: Essay content
            title: Essay title
            
        Returns:
            Dict: Analysis results
        """
        logger.info(f"Starting essay analysis: {title or 'No title'}")
        
        try:
            # Construct analysis prompt
            system_prompt = self.config['ANALYSIS_SYSTEM_PROMPT']
            user_prompt = f"""Please provide a deep analysis of the following essay and return results in JSON format.

Essay title: {title or "No title"}

Essay content:
{essay_text}

Please return the analysis results in the following JSON format:
{{
    "theme": "Theme analysis",
    "keywords": ["keyword1", "keyword2", "..."],
    "sentiment": "Sentiment tendency", 
    "complexity": "Complexity analysis",
    "style": "Writing style",
    "strengths": ["strength1", "strength2", "..."],
    "weaknesses": ["weakness1", "weakness2", "..."],
    "summary": "Summary"
}}

Note: 
1. Output in JSON format only
2. Please provide detailed explanations based on actual issues
3. Error types can be chosen from: grammar, spelling, punctuation, word_choice, verb_tense, subject_verb_agreement, article, preposition, pronoun, word_order, redundancy, missing_word, collocation
4. Scoring guidelines: 90-100 (excellent), 80-89 (good), 70-79 (average), 60-69 (passing), 0-59 (failing)
5. Only output pure JSON content without quotes or placeholders"""

            # Call AI API
            response = self._call_ai_api(system_prompt, user_prompt)
            
            # Parse results
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # If direct parsing fails, try to extract JSON part
                try:
                    json_match = response.strip()
                    if json_match.startswith('```json'):
                        json_match = json_match.replace('```json', '').replace('```', '')
                    elif json_match.startswith('```'):
                        json_match = json_match.replace('```', '')
                    
                    result = json.loads(json_match.strip())
                except:
                    raise ValueError("Essay analysis failed: Invalid JSON format")
            
            result['success'] = True
            return result
            
        except Exception as e:
            logger.error(f"Essay analysis failed: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_correction_rules(self) -> Dict:
        """Get correction rules
        
        Returns:
            Dict: Rules for essay correction
        """
        return SCORING_RULES
    
    def get_error_types(self) -> List[str]:
        """Get error types
        
        Returns:
            List[str]: List of error types
        """
        return ERROR_TYPES

