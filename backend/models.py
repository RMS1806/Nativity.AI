"""
Pydantic Models for Nativity.ai API
Defines request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TargetLanguage(str, Enum):
    """Supported target languages for localization"""
    HINDI = "hindi"
    TAMIL = "tamil"
    BENGALI = "bengali"
    TELUGU = "telugu"
    MARATHI = "marathi"


class VideoUploadRequest(BaseModel):
    """Request for generating presigned upload URL"""
    file_name: str = Field(..., description="Name of the video file")
    content_type: str = Field(default="video/mp4", description="MIME type")


class VideoUploadResponse(BaseModel):
    """Response with presigned upload URL"""
    upload_url: str
    file_key: str
    bucket: str
    expires_in: int


class LocalizationRequest(BaseModel):
    """Request to start video localization"""
    file_key: str = Field(..., description="S3 key of uploaded video")
    target_language: TargetLanguage = Field(
        default=TargetLanguage.HINDI,
        description="Target language for localization"
    )


class CulturalAdaptation(BaseModel):
    """Cultural adaptation details for a segment"""
    has_idiom: bool = False
    original_idiom: Optional[str] = None
    adapted_meaning: Optional[str] = None
    adaptation_note: Optional[str] = None


class OnScreenText(BaseModel):
    """On-screen text detection for a segment"""
    detected: bool = False
    original: Optional[str] = None
    translated: Optional[str] = None


class VideoSegment(BaseModel):
    """A single segment of the video with translation"""
    id: int
    start_time: str
    end_time: str
    speaker: str
    original_text: str
    translated_text: str
    cultural_adaptation: CulturalAdaptation
    on_screen_text: OnScreenText


class CulturalSensitivity(BaseModel):
    """Detected cultural sensitivity item"""
    timestamp: str
    description: str
    recommendation: str


class CulturalReport(BaseModel):
    """Overall cultural analysis report"""
    idioms_adapted: int
    cultural_sensitivities: List[CulturalSensitivity]
    localization_quality_score: int
    notes: str


class TTSInstructions(BaseModel):
    """Text-to-speech generation instructions"""
    recommended_voice_gender: str
    pacing_notes: str
    emotion_markers: List[str]


class VideoMetadata(BaseModel):
    """Video metadata from analysis"""
    duration_seconds: float
    detected_speakers: int
    content_type: str


class LocalizationResult(BaseModel):
    """Complete localization analysis result"""
    video_metadata: VideoMetadata
    segments: List[VideoSegment]
    cultural_report: CulturalReport
    tts_instructions: TTSInstructions
    source_language: str = "english"
    target_language: str


class JobStatus(str, Enum):
    """Status of a localization job"""
    PENDING = "pending"
    UPLOADING = "uploading"
    ANALYZING = "analyzing"
    GENERATING_AUDIO = "generating_audio"
    STITCHING = "stitching"
    COMPLETE = "complete"
    FAILED = "failed"


class LocalizationJob(BaseModel):
    """Localization job tracking"""
    job_id: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    message: str
    input_file: str
    target_language: str
    output_file: Optional[str] = None
    error: Optional[str] = None


class QuickTranslateRequest(BaseModel):
    """Request for quick text translation"""
    text: str = Field(..., description="Text to translate")
    target_language: TargetLanguage = Field(default=TargetLanguage.HINDI)


class QuickTranslateResponse(BaseModel):
    """Response from quick translation"""
    original: str
    translated: str
    has_adaptation: bool
    adaptation_note: Optional[str] = None
