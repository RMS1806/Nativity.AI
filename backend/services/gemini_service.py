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
INITIAL_RETRY_DELAY_SECONDS = 15  # Doubles with each attempt (15s → 30s → 60s)
API_TIMEOUT_SECONDS = 180          # Hard timeout per API call (Gemini 2.5-flash needs time for video)

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
        video_path: str = None,
        video_url: str = None,
        target_language: str = "hindi",
        continuation_context: str = None,
    ) -> dict:
        """
        Analyze video and generate localization data.

        Accepts either a local file path (video_path) or a publicly accessible
        URL (video_url). When video_url is supplied Gemini fetches the file
        itself — no download to local disk, no Files API upload, no wait loop.
        This is the preferred path when R2_PUBLIC_URL is configured because it
        avoids writing the input video to Render's ephemeral disk at all.

        Falls back to the Files API upload path when only video_path is given.
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured. Set GOOGLE_API_KEY."}

        if not video_path and not video_url:
            return {"error": "Either video_path or video_url must be provided"}

        # ── Build the video content part ──────────────────────────────────────
        if video_url:
            # URL path: Gemini fetches the video directly — zero local disk use.
            print(f"🔗 Using video URL for Gemini (no download needed): {video_url[:80]}...")
            try:
                video_content = types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")
            except Exception as e:
                return {"error": f"Failed to create URI part: {str(e)}"}
        else:
            # Files API path: upload local file, wait for Gemini to process it.
            try:
                print(f"📤 Uploading video file to Gemini Files API: {video_path}")
                video_file = self.client.files.upload(file=video_path)
                print(f"📁 File uploaded: {video_file.name}")

                print("⏳ Waiting for Gemini video processing...")
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = self.client.files.get(name=video_file.name)
                    print(f"   State: {video_file.state.name}")

                if video_file.state.name == "FAILED":
                    return {"error": "Video processing failed in Gemini Files API"}

                print("✅ Video ready for analysis")
                video_content = video_file
            except Exception as e:
                return {"error": f"Failed to upload video: {str(e)}"}

        # ── Generate analysis ─────────────────────────────────────────────────
        prompt = self._build_analysis_prompt(target_language, continuation_context)
        print(f"Sending payload of length: {len(prompt)} (+ video)")

        response = None
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🧠 Generating analysis (attempt {attempt + 1}/{MAX_RETRIES})...")
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[video_content, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                print("✅ Analysis complete")
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
                    print(f"⚠️ Service unavailable. Retrying in {delay}s...")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"status": "failed", "reason": "LLM service temporarily unavailable. Please try again later."}
                else:
                    raise e

        if response is None:
            return {"error": "Failed to get response from Gemini API"}

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
        video_path: str = None,
        video_url: str = None,
        target_language: str = "hindi"
    ) -> dict:
        """
        Phase 1: Generate translation draft for human review.
        Accepts either video_path (local file) or video_url (public URL).
        """
        analysis = await self.analyze_video(
            video_path=video_path,
            video_url=video_url,
            target_language=target_language,
        )
        
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
    
    async def analyze_audio(
        self,
        audio_path: str,
        target_language: str = "hindi",
    ) -> dict:
        """
        Analyze a local audio file (extracted from video) instead of the full video.
        Uses Gemini Files API — audio files are tiny vs video, so no time limit issues.
        Returns the same segment dict format as analyze_video.
        """
        if not self.is_configured():
            return {"error": "Gemini API not configured. Set GOOGLE_API_KEY."}

        try:
            ext = Path(audio_path).suffix.lower()
            mime = "audio/mp4" if ext in (".m4a", ".mp4", ".aac") else "audio/mpeg"
            print(f"📤 Uploading audio to Gemini Files API: {audio_path} ({mime})")
            audio_file = self.client.files.upload(file=audio_path, config={"mime_type": mime})
            print(f"📁 Audio uploaded: {audio_file.name}")

            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = self.client.files.get(name=audio_file.name)

            if audio_file.state.name == "FAILED":
                return {"error": "Audio processing failed in Gemini Files API"}

            print("✅ Audio ready for analysis")
        except Exception as e:
            return {"error": f"Failed to upload audio: {str(e)}"}

        prompt = self._build_analysis_prompt(target_language)
        print(f"Sending audio payload (+ prompt len={len(prompt)})")

        response = None
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🧠 Analyzing audio (attempt {attempt + 1}/{MAX_RETRIES})...")
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[audio_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                print("✅ Audio analysis complete")
                break
            except TimeoutError as e:
                if attempt == MAX_RETRIES - 1:
                    return {"status": "failed", "reason": "API Timeout — try a shorter clip."}
                time.sleep(INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt))
            except Exception as e:
                error_str = str(e).lower()
                print(f"❌ Gemini audio error on attempt {attempt + 1}: {e}")
                if any(err in error_str for err in ["resourceexhausted", "429", "quota"]):
                    if attempt == MAX_RETRIES - 1:
                        return {"status": "failed", "reason": "Quota exceeded. Try again soon."}
                    time.sleep(INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt))
                else:
                    raise e

        if response is None:
            return {"error": "Failed to get response from Gemini API"}

        try:
            result = json.loads(response.text)
            result["source_language"] = "english"
            result["target_language"] = target_language
            return result
        except json.JSONDecodeError:
            return {"error": "Failed to parse Gemini response", "raw_response": response.text}

    def _build_analysis_prompt(self, target_language: str, continuation_context: str = None) -> str:
        """Build the comprehensive analysis prompt"""
        
        language_map = {
            "hindi": "Hindi (हिंदी)",
            "tamil": "Tamil (தமிழ்)",
            "bengali": "Bengali (বাংলা)",
            "telugu": "Telugu (తెలుగు)",
            "marathi": "Marathi (मराठी)"
        }
        
        target_lang_display = language_map.get(target_language, target_language)
        
        continuation_note = ""
        if continuation_context:
            continuation_note = (
                f"\nIMPORTANT — CHUNK CONTEXT: This video is a continuation segment. "
                f"The previous chunk ended with the speaker saying: \"{continuation_context}\". "
                f"Ensure translation style, terminology, and speaker identity stay consistent with that context.\n"
            )

        return f'''You are Nativity.ai, an expert localization agent specializing in adapting English content for Indian audiences.
{continuation_note}

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
9. LENGTH-MATCH FOR DUBBING: Each segment will be dubbed into the time window between its start_time and end_time. Keep "translated_text" close to the ORIGINAL spoken duration of that segment — prefer concise, natural phrasing that a speaker could comfortably say in that many seconds. Drop filler words and avoid padding. When {target_lang_display} would naturally be longer than the English, tighten the wording (transcreate, don't pad). It is better to be slightly shorter than to overflow the segment's time window.

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

    async def generate_shorts_suggestions(
        self, video_url: str, target_count: int = 5, video_duration_s: float = 0
    ) -> list:
        """
        Analyze a video and return clip suggestions for short-form content.
        Each clip is 45-90 seconds, chosen for standalone engagement value.
        Returns list of {title, start_time_s, end_time_s, description} dicts.
        """
        if not self.is_configured():
            return []

        duration_line = (
            f"- The video is exactly {video_duration_s:.1f} seconds long. "
            f"All timestamps MUST be within 0–{video_duration_s:.1f}s.\n"
            if video_duration_s > 0
            else ""
        )

        # Adapt clip length to the actual video duration
        if video_duration_s > 0 and video_duration_s < 60:
            min_clip = max(5, int(video_duration_s * 0.3))
            max_clip = int(video_duration_s * 0.9)
            clip_rule = f"- Each clip must be between {min_clip} and {max_clip} seconds long (video is short)"
        else:
            clip_rule = "- Each clip must be between 45 and 90 seconds long"

        prompt = f"""Analyze this video and identify the {target_count} best moments to extract as short-form clips (YouTube Shorts or Instagram Reels style).

Rules:
{duration_line}{clip_rule}
- Clips must not overlap
- Prioritize: key insights, surprising moments, clear standalone value, strong openings
- Avoid: intros, outros, quiet transitions, mid-sentence cuts

Return a JSON object with exactly this structure:
{{
  "clips": [
    {{
      "title": "Concise clip title (max 60 characters)",
      "start_time_s": 12.5,
      "end_time_s": 78.3,
      "description": "One sentence on why this moment works as a standalone short"
    }}
  ]
}}

Return up to {target_count} clips ordered by engagement potential (best first). If the video is too short for {target_count} non-overlapping clips, return fewer."""

        try:
            video_part = types.Part.from_uri(file_uri=video_url, mime_type="video/mp4")
        except Exception as e:
            print(f"[Shorts] Failed to build video part: {e}")
            return []

        response = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[Shorts] Gemini clip analysis attempt {attempt}/{MAX_RETRIES}...")
                response = self.client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[video_part, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )
                data = json.loads(response.text)
                clips = data.get("clips", [])
                print(f"[Shorts] Got {len(clips)} clip suggestions")
                return clips
            except Exception as e:
                print(f"[Shorts] Attempt {attempt} failed: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(15 * attempt)
        return []


# Singleton instance
gemini_service = GeminiService()
