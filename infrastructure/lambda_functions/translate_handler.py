"""
Lambda Function: Translate Handler
Quick text translation using Google Gemini
"""

import json
import os
from typing import Dict, Any
import google.generativeai as genai

# Environment variables
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Quick text translation with cultural adaptation
    
    Expected input:
    {
        "text": "Hello world",
        "target_language": "hindi"
    }
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        text = body.get('text')
        target_language = body.get('target_language', 'hindi')
        
        if not text:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'text is required'
                })
            }
        
        # Language mapping
        language_map = {
            'hindi': 'Hindi (हिंदी)',
            'tamil': 'Tamil (தமிழ்)',
            'bengali': 'Bengali (বাংলা)',
            'telugu': 'Telugu (తెలుగు)',
            'marathi': 'Marathi (मराठी)'
        }
        
        target_lang_display = language_map.get(target_language, target_language)
        
        # Create prompt for cultural adaptation
        prompt = f'''Translate this English text to {target_lang_display} with cultural adaptation for Indian audiences.
If there are idioms or cultural references, adapt them appropriately.

Text: "{text}"

Return JSON:
{{
  "original": "<original text>",
  "translated": "<translated text>",
  "has_adaptation": <boolean>,
  "adaptation_note": "<explanation if adapted>"
}}'''
        
        # Generate translation
        response = model.generate_content(prompt)
        
        # Parse response
        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            result = {
                "original": text,
                "translated": response.text,
                "has_adaptation": False,
                "adaptation_note": None
            }
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Error in translate_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': 'Translation failed',
                'message': str(e)
            })
        }