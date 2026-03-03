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
from google.api_core.exceptions import GoogleAPIError
from config import settings

# Retry / timeout configuration
MAX_RETRIES = 3                    # Max attempts before giving up
INITIAL_RETRY_DELAY_SECONDS = 5   # Doubles with each attempt (5s → 10s → 20s)
API_TIMEOUT_SECONDS = 60           # Hard timeout per API call

# Model selection - Gemini 2.0 Flash (stable GA, high availability)
MODEL_NAME = "gemini-2.5-flash"


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
            self.client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(timeout=API_TIMEOUT_SECONDS * 1000),  # ms
            )
            print(f"✅ Gemini client initialized with model: {MODEL_NAME} (timeout={API_TIMEOUT_SECONDS}s)")
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
        
        # Generate analysis with video context (retry loop with backoff)
        print(f"Sending payload of length: {len(prompt)} (+ video file)")
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
            except TimeoutError as e:
                print(f"⏱️ Timeout on attempt {attempt + 1}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"status": "failed", "reason": "LLM API Timeout - Please try a shorter video or try again later."}
                time.sleep(INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt))
            except Exception as e:
                error_str = str(e).lower()
                print(f"❌ Gemini error on attempt {attempt + 1}: {e}")
                if any(err in error_str for err in ["resourceexhausted", "429", "quota"]):
                    if attempt == MAX_RETRIES - 1:
                        return {"status": "failed", "reason": "LLM API Quota Exceeded. Please try again soon."}
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"⚠️ Quota hit. Retrying in {delay}s...")
                    time.sleep(delay)
                elif any(err in error_str for err in ["503", "serviceunavailable", "overloaded"]):
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"⚠️ Service unavailable. Retrying in {delay}s...")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"status": "failed", "reason": "LLM service temporarily unavailable. Please try again later."}
                else:
                    raise e  # Re-raise unexpected errors immediately
        
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
    "content_type": "<educational|entertainment|promotional|informational>",
    "first_speech_offset_seconds": <seconds until first spoken word, e.g. 2.5 if there's intro music>
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
8. CRITICAL: Accurately detect first_speech_offset_seconds - if there's intro music, silence, or ambiance before the first spoken word, return that offset in seconds (e.g., 2.5). If speech starts immediately, return 0

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

        # Retry logic with exponential backoff
        print(f"Sending payload of length: {len(prompt)}")
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
            except TimeoutError as e:
                print(f"⏱️ Timeout on attempt {attempt + 1}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return {"status": "failed", "reason": "LLM API Timeout - Please try a shorter video or try again later."}
                time.sleep(INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt))
            except Exception as e:
                error_str = str(e).lower()
                print(f"❌ Gemini error on attempt {attempt + 1}: {e}")
                if any(err in error_str for err in ["resourceexhausted", "429", "quota"]):
                    if attempt == MAX_RETRIES - 1:
                        return {"status": "failed", "reason": "LLM API Quota Exceeded. Please try again soon."}
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    print(f"⚠️ Quota hit. Retrying in {delay}s...")
                    time.sleep(delay)
                elif any(err in error_str for err in ["503", "serviceunavailable", "overloaded"]):
                    delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"status": "failed", "reason": "LLM service temporarily unavailable. Please try again later."}
                else:
                    raise e
        
        if response is None:
            return {"error": "Failed to get response from Gemini API"}
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {"error": "Parse error", "raw": response.text}

    async def generate_metadata(
        self,
        translated_text: str,
        target_language: str,
    ) -> dict:
        """
        Generate SEO-optimized YouTube metadata for localized videos.
        
        Args:
            translated_text: The full translated transcript of the video
            target_language: Language the video was localized to
        
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
        
        prompt = f"""
You are an expert YouTube SEO strategist. I will provide you with the exact spoken transcript of a video that has been localized into {target_lang_display}. 

Your job is to generate highly engaging, click-optimized YouTube metadata strictly based on the content of this transcript. The output MUST be entirely in {target_lang_display}.

Video Transcript:
"{translated_text}"

You MUST respond ONLY with a raw, valid JSON object using exactly these keys. Do not include markdown blocks or introductory text.
{{
    "title": "A catchy, high-CTR YouTube title (under 70 characters)",
    "description": "A 2-3 paragraph YouTube description summarizing the video value, naturally including SEO keywords",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"]
}}
"""

        # Retry logic – while loop with linear backoff, max 2 attempts
        print(f"Sending payload of length: {len(prompt)}")
        attempt = 0
        max_retries = 2

        while attempt < max_retries:
            try:
                attempt += 1
                print(f"🧠 Generating YouTube metadata (attempt {attempt}/{max_retries})...")

                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )

                # Parse and return
                raw_text = response.text.strip()
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("\n", 1)[-1]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[: raw_text.rfind("```")].strip()
                result = json.loads(raw_text)
                result["language"] = target_language
                return result

            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e}")
                return {
                    "title": "Format Error - Could not parse response",
                    "description": "The AI returned an invalid format. Please try again.",
                    "tags": ["error"],
                    "language": target_language,
                }

            except GoogleAPIError as e:
                print(f"❌ Gemini API Error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    sleep_time = 5 * attempt
                    print(f"⚠️ Service unavailable. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    print("🚨 Max retries reached.")
                    return {
                        "title": "API Overloaded - Please try again later",
                        "description": "The AI service is currently busy.",
                        "tags": ["error"],
                        "language": target_language,
                    }

            except Exception as e:
                print(f"❌ Unexpected Error: {e}")
                return {
                    "title": "System Error",
                    "description": "An unexpected error occurred.",
                    "tags": ["error"],
                    "language": target_language,
                }

        # Should not reach here, but guard anyway
        return {"error": "Failed to get response from Gemini API"}



# Singleton instance
gemini_service = GeminiService()
