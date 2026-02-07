"""
Text-to-Speech Service for Nativity.ai
Generates localized audio using edge-tts (Microsoft Edge TTS)

edge-tts provides high-quality, free TTS with excellent Indian language support
and multiple voice options per language.
"""

import asyncio
import edge_tts
import os
import tempfile
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class AudioSegment:
    """Represents a generated audio segment"""
    text: str
    file_path: str
    start_time: str
    end_time: str
    duration_ms: int
    language: str


class TTSService:
    """
    Text-to-Speech service using edge-tts
    Supports multiple Indian languages with natural-sounding voices
    """
    
    # Voice mapping for Indian languages
    # Format: language_code -> (voice_name, display_name)
    VOICE_MAP = {
        "hindi": {
            "male": "hi-IN-MadhurNeural",
            "female": "hi-IN-SwaraNeural"
        },
        "tamil": {
            "male": "ta-IN-ValluvarNeural",
            "female": "ta-IN-PallaviNeural"
        },
        "bengali": {
            "male": "bn-IN-BashkarNeural",
            "female": "bn-IN-TanishaaNeural"
        },
        "telugu": {
            "male": "te-IN-MohanNeural",
            "female": "te-IN-ShrutiNeural"
        },
        "marathi": {
            "male": "mr-IN-ManoharNeural",
            "female": "mr-IN-AarohiNeural"
        },
        "english": {
            "male": "en-IN-PrabhatNeural",
            "female": "en-IN-NeerjaNeural"
        }
    }
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize TTS service
        
        Args:
            output_dir: Directory for storing generated audio files
        """
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="nativity_tts_")
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_voice(self, language: str, gender: str = "female") -> str:
        """
        Get the appropriate voice for a language
        
        Args:
            language: Target language code
            gender: 'male' or 'female'
        
        Returns:
            Voice name string
        """
        lang_voices = self.VOICE_MAP.get(language.lower(), self.VOICE_MAP["hindi"])
        return lang_voices.get(gender, lang_voices["female"])
    
    async def generate_audio_segment(
        self,
        text: str,
        language: str,
        file_path: str,
        gender: str = "female",
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ) -> dict:
        """
        Generate a single audio segment from text
        
        Args:
            text: Text to convert to speech
            language: Target language (hindi, tamil, bengali, etc.)
            file_path: Path to save the audio file
            gender: Voice gender preference
            rate: Speech rate adjustment (e.g., "+10%", "-5%")
            pitch: Pitch adjustment
        
        Returns:
            dict with file_path, duration, and status
        """
        try:
            voice = self.get_voice(language, gender)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Create communicator with voice settings
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            
            # Generate and save audio
            await communicate.save(file_path)
            
            # Get audio duration (optional - requires pydub)
            duration_ms = await self._get_audio_duration(file_path)
            
            return {
                "success": True,
                "file_path": file_path,
                "voice": voice,
                "language": language,
                "duration_ms": duration_ms,
                "text_length": len(text)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file_path": file_path
            }
    
    async def generate_segments_from_analysis(
        self,
        segments: List[dict],
        language: str,
        gender: str = "female"
    ) -> List[AudioSegment]:
        """
        Generate audio for all segments from Gemini analysis
        
        Args:
            segments: List of segment dicts from Gemini analysis
            language: Target language
            gender: Voice gender preference
        
        Returns:
            List of AudioSegment objects
        """
        audio_segments = []
        
        for i, segment in enumerate(segments):
            # Generate unique filename
            filename = f"segment_{i:04d}.mp3"
            file_path = os.path.join(self.output_dir, filename)
            
            # Get translated text
            text = segment.get("translated_text", "")
            if not text:
                continue
            
            # Generate audio
            result = await self.generate_audio_segment(
                text=text,
                language=language,
                file_path=file_path,
                gender=gender
            )
            
            if result["success"]:
                audio_segments.append(AudioSegment(
                    text=text,
                    file_path=file_path,
                    start_time=segment.get("start_time", "00:00"),
                    end_time=segment.get("end_time", "00:00"),
                    duration_ms=result.get("duration_ms", 0),
                    language=language
                ))
        
        return audio_segments
    
    async def _get_audio_duration(self, file_path: str) -> int:
        """
        Get audio duration in milliseconds
        Falls back to 0 if pydub is not available
        """
        try:
            from pydub import AudioSegment as PydubSegment
            audio = PydubSegment.from_mp3(file_path)
            return len(audio)
        except ImportError:
            # pydub not installed, return 0
            return 0
        except Exception:
            return 0
    
    @staticmethod
    async def list_available_voices(language_filter: Optional[str] = None) -> List[dict]:
        """
        List all available voices from edge-tts
        
        Args:
            language_filter: Optional filter by language code (e.g., 'hi-IN')
        
        Returns:
            List of voice info dicts
        """
        voices = await edge_tts.list_voices()
        
        if language_filter:
            voices = [v for v in voices if language_filter.lower() in v["Locale"].lower()]
        
        return [
            {
                "name": v["ShortName"],
                "locale": v["Locale"],
                "gender": v["Gender"],
                "friendly_name": v["FriendlyName"]
            }
            for v in voices
        ]
    
    def cleanup(self):
        """Remove all generated audio files"""
        import shutil
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)


# Singleton instance
tts_service = TTSService()


# Convenience function for synchronous usage
def generate_audio_sync(text: str, language: str, file_path: str, gender: str = "female") -> dict:
    """Synchronous wrapper for generate_audio_segment"""
    return asyncio.run(tts_service.generate_audio_segment(text, language, file_path, gender))
