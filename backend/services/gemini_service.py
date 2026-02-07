"""
Gemini AI Service - The Brain of Nativity.ai
Handles video analysis, transcription, OCR, and cultural transcreation
Using the new google-genai SDK for Gemini 3 support
"""

import os
import json
import time
from pathlib import Path
from typing import Optional
from google import genai
from google.genai import types
from config import settings

# Stubborn retry configuration for large video processing
MAX_RETRIES = 10
INITIAL_RETRY_DELAY_SECONDS = 5  # Doubles with each attempt (exponential backoff)

# Model selection - Gemini 3 Flash Preview
MODEL_NAME = "gemini-3-flash-preview"


class GeminiService:
    """
    Service for interacting with Google Gemini 3
    Leverages multimodal capabilities for video understanding
    Uses the new google-genai SDK
    """
    
    def __init__(self):
        self.api_key = settings.GOOGLE_API_KEY
        self.client = None
        self._configure()
    
    def _configure(self):
        """Configure the Gemini API client using new SDK"""
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            print(f"✅ Gemini client initialized with model: {MODEL_NAME}")
        else:
            print("⚠️ GOOGLE_API_KEY not found - Gemini client not initialized")
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if Gemini API is properly configured"""
        return self.client is not None
    
    async def analyze_video(
        self, 
        video_path: str, 
        target_language: str = "hindi"
    ) -> dict:
        """
        Analyze video and generate localization data
        
        Args:
            video_path: Path to the video file
            target_language: Target language for translation (hindi, tamil, bengali)
        
        Returns:
            dict containing transcript, translations, timestamps, and cultural notes
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured. Set GOOGLE_API_KEY."}
        
        try:
            # Upload video file to Gemini using new SDK
            print(f"📤 Uploading video file: {video_path}")
            video_file = self.client.files.upload(file=video_path)
            print(f"📁 File uploaded: {video_file.name}")
            
            # Wait for file processing
            print("⏳ Waiting for video processing...")
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = self.client.files.get(name=video_file.name)
                print(f"   State: {video_file.state.name}")
            
            if video_file.state.name == "FAILED":
                return {"error": "Video processing failed"}
            
            print("✅ Video ready for analysis")
            
        except Exception as e:
            return {"error": f"Failed to upload video: {str(e)}"}
        
        # The magic prompt for cultural transcreation
        prompt = self._build_analysis_prompt(target_language)
        
        # Generate analysis with video context (stubborn retry loop for large videos)
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🧠 Generating analysis (attempt {attempt + 1}/{MAX_RETRIES})...")
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[video_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                print("✅ Analysis complete")
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e).lower()
                # Catch ResourceExhausted and ServiceUnavailable
                if any(err in error_str for err in ["resourceexhausted", "429", "quota", "503", "serviceunavailable", "overloaded"]):
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s, 40s...
                    print(f"⚠️ Gemini is busy. Retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"error": "API quota exceeded after multiple retries. Please wait and try again."}
                else:
                    raise e  # Re-raise other errors
        
        if response is None:
            return {"error": "Failed to get response from Gemini API"}
        
        # Parse and return structured response
        try:
            result = json.loads(response.text)
            result["source_language"] = "english"
            result["target_language"] = target_language
            return result
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse Gemini response",
                "raw_response": response.text
            }
    
    async def generate_translation_draft(
        self, 
        video_path: str, 
        target_language: str = "hindi"
    ) -> dict:
        """
        Phase 1: Generate translation draft for human review.
        Performs transcription and translation but does NOT run TTS or dubbing.
        
        Args:
            video_path: Path to the video file
            target_language: Target language for translation
        
        Returns:
            dict containing:
                - segments: List of {start, end, original_text, translated_text}
                - cultural_analysis: List of cultural adaptations made
                - video_title: Detected/suggested title
                - ready_for_review: True if segments are ready
        """
        # Use the existing analyze_video method
        analysis = await self.analyze_video(video_path, target_language)
        
        if "error" in analysis:
            return analysis
        
        # Extract and structure segments for human review
        segments = analysis.get("segments", [])
        
        # Ensure each segment has the required fields for editing
        draft_segments = []
        for i, seg in enumerate(segments):
            draft_segments.append({
                "index": i,
                "start": seg.get("start_time", seg.get("start", 0)),
                "end": seg.get("end_time", seg.get("end", 0)),
                "original_text": seg.get("original_text", seg.get("text", "")),
                "translated_text": seg.get("translated_text", seg.get("translation", "")),
                "cultural_notes": seg.get("cultural_notes", ""),
                "is_approved": False  # Human hasn't approved yet
            })
        
        return {
            "segments": draft_segments,
            "cultural_analysis": analysis.get("cultural_analysis", []),
            "video_title": analysis.get("video_title", "Untitled Video"),
            "detected_language": analysis.get("detected_language", "english"),
            "target_language": target_language,
            "total_segments": len(draft_segments),
            "ready_for_review": len(draft_segments) > 0,
            # Keep full analysis for later use
            "_full_analysis": analysis
        }
    
    def _build_analysis_prompt(self, target_language: str) -> str:
        """Build the comprehensive analysis prompt"""
        
        language_map = {
            "hindi": "Hindi (हिंदी)",
            "tamil": "Tamil (தமிழ்)",
            "bengali": "Bengali (বাংলা)",
            "telugu": "Telugu (తెలుగు)",
            "marathi": "Marathi (मराठी)"
        }
        
        target_lang_display = language_map.get(target_language, target_language)
        
        return f'''You are Nativity.ai, an expert localization agent specializing in adapting English content for Indian audiences.

Analyze this video comprehensively and provide a JSON response with the following structure:

{{
  "video_metadata": {{
    "duration_seconds": <total duration>,
    "detected_speakers": <number of unique speakers>,
    "content_type": "<educational|entertainment|promotional|informational>"
  }},
  "segments": [
    {{
      "id": <segment number>,
      "start_time": "<MM:SS>",
      "end_time": "<MM:SS>",
      "speaker": "<speaker identifier>",
      "original_text": "<exact English speech>",
      "translated_text": "<{target_lang_display} translation>",
      "cultural_adaptation": {{
        "has_idiom": <boolean>,
        "original_idiom": "<if applicable>",
        "adapted_meaning": "<culturally appropriate version>",
        "adaptation_note": "<explanation of cultural change>"
      }},
      "on_screen_text": {{
        "detected": <boolean>,
        "original": "<English text on screen>",
        "translated": "<translated text>"
      }}
    }}
  ],
  "cultural_analysis": [
    {{
      "timestamp": "<MM:SS>",
      "type": "<idiom|metaphor|reference|gesture|sensitivity>",
      "context": "<what was detected in the original>",
      "adaptation": "<how it was adapted for {target_lang_display}>",
      "reasoning": "<why this adaptation was chosen, cultural insight>"
    }}
  ],
  "cultural_report": {{
    "idioms_adapted": <count>,
    "cultural_sensitivities": [
      {{
        "timestamp": "<MM:SS>",
        "description": "<what was detected>",
        "recommendation": "<suggestion for Indian audience>"
      }}
    ],
    "localization_quality_score": <1-10>,
    "notes": "<overall cultural adaptation notes>"
  }},
  "tts_instructions": {{
    "recommended_voice_gender": "<male|female|mixed>",
    "pacing_notes": "<speed adjustments needed>",
    "emotion_markers": ["<list of emotional tones detected>"]
  }}
}}

CRITICAL INSTRUCTIONS:
1. TRANSCREATE, don't just translate - adapt idioms, metaphors, and cultural references for {target_lang_display} speakers
2. Example: "Piece of cake" should become "बाएं हाथ का खेल" (left hand's game) in Hindi, NOT "Cake ka tukda"
3. Identify ALL text visible on screen (slides, signs, captions)
4. Note any culturally sensitive imagery or gestures
5. Preserve technical terms when translation would lose meaning
6. Ensure timestamps are accurate for lip-sync
7. IMPORTANT: Populate the "cultural_analysis" array with EVERY cultural adaptation made, explaining the reasoning

Return ONLY valid JSON, no additional text.'''

    async def quick_translate(
        self, 
        text: str, 
        target_language: str = "hindi"
    ) -> dict:
        """
        Quick text translation with cultural adaptation
        For testing without video upload
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured"}
        
        prompt = f'''Translate this English text to {target_language} with cultural adaptation for Indian audiences.
If there are idioms or cultural references, adapt them appropriately.

Text: "{text}"

Return JSON:
{{
  "original": "<original text>",
  "translated": "<translated text>",
  "has_adaptation": <boolean>,
  "adaptation_note": "<explanation if adapted>"
}}'''

        # Stubborn retry logic with exponential backoff
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                break  # Success, exit retry loop
            except Exception as e:
                error_str = str(e).lower()
                # Catch ResourceExhausted and ServiceUnavailable
                if any(err in error_str for err in ["resourceexhausted", "429", "quota", "503", "serviceunavailable", "overloaded"]):
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"⚠️ Gemini is busy. Retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"error": "API quota exceeded after multiple retries. Please wait and try again."}
                else:
                    raise e  # Re-raise other errors
        
        if response is None:
            return {"error": "Failed to get response from Gemini API"}
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Parse error", "raw": response.text}

    async def generate_metadata(
        self,
        video_title: str,
        target_language: str,
        original_description: str = ""
    ) -> dict:
        """
        Generate SEO-optimized YouTube metadata for localized videos
        
        Args:
            video_title: Original video title
            target_language: Language the video was localized to
            original_description: Optional original description for context
        
        Returns:
            dict with title, description, and tags for YouTube
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured"}
        
        language_map = {
            "hindi": "Hindi (हिंदी)",
            "tamil": "Tamil (தமிழ்)",
            "bengali": "Bengali (বাংলা)",
            "telugu": "Telugu (తెలుగు)",
            "marathi": "Marathi (मराठी)"
        }
        
        target_lang_display = language_map.get(target_language, target_language)
        
        prompt = f'''You are a YouTube SEO expert specializing in Indian language content.

Generate optimized YouTube metadata for a video that has been localized to {target_lang_display}.

Original Video Title: "{video_title}"
{f'Original Description: "{original_description}"' if original_description else ''}

Create SEO-optimized metadata in {target_lang_display} that will maximize discoverability for Indian audiences.

Return JSON in this exact format:
{{
  "title": "<SEO-optimized title in {target_lang_display}, max 100 chars, include key terms>",
  "description": "<Engaging description in {target_lang_display}, 200-500 chars, include relevant keywords, call-to-action>",
  "tags": ["<15-20 relevant tags in {target_lang_display} and English mix for maximum reach>"]
}}

GUIDELINES:
1. Title should be catchy and include the primary keyword
2. Description should have a hook in the first line (visible in search results)
3. Include both {target_lang_display} and English tags for broader discoverability
4. Tags should include: language name, topic keywords, related terms, trending phrases
5. Add relevant hashtags potential in the description
6. Keep cultural context in mind for the Indian audience

Return ONLY valid JSON, no additional text.'''

        # Stubborn retry logic with exponential backoff
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                break
            except Exception as e:
                error_str = str(e).lower()
                # Catch ResourceExhausted and ServiceUnavailable
                if any(err in error_str for err in ["resourceexhausted", "429", "quota", "503", "serviceunavailable", "overloaded"]):
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"⚠️ Gemini is busy. Retrying in {delay} seconds... (Attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"error": "API quota exceeded after multiple retries. Please wait and try again."}
                else:
                    raise e
        
        if response is None:
            return {"error": "Failed to get response from Gemini API"}
        
        try:
            result = json.loads(response.text)
            result["language"] = target_language
            return result
        except json.JSONDecodeError:
            return {"error": "Parse error", "raw": response.text}


# Singleton instance
gemini_service = GeminiService()
