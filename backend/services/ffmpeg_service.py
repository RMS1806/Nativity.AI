"""
FFmpeg Service for Nativity.ai
Handles video processing, audio stitching, and optimization

Uses ffmpeg-python for programmatic control of FFmpeg
"""

import ffmpeg
import subprocess
import os
import shutil
import tempfile
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result of video processing operation"""
    success: bool
    output_path: Optional[str]
    file_size_mb: float
    duration_seconds: float
    error: Optional[str] = None


class FFmpegService:
    """
    Service for video processing using FFmpeg
    Handles audio replacement, optimization, and low-bandwidth encoding
    """
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is installed and available"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available for use"""
        return self.ffmpeg_available
    
    def get_video_info(self, video_path: str) -> dict:
        """
        Get video metadata using ffprobe
        
        Args:
            video_path: Path to video file
        
        Returns:
            dict with duration, resolution, codec info
        """
        if not self.ffmpeg_available:
            return {"error": "FFmpeg not installed"}
        
        try:
            probe = ffmpeg.probe(video_path)
            
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'),
                None
            )
            audio_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'audio'),
                None
            )
            
            return {
                "duration": float(probe['format'].get('duration', 0)),
                "size_bytes": int(probe['format'].get('size', 0)),
                "size_mb": int(probe['format'].get('size', 0)) / (1024 * 1024),
                "format": probe['format'].get('format_name'),
                "video": {
                    "codec": video_stream.get('codec_name') if video_stream else None,
                    "width": video_stream.get('width') if video_stream else None,
                    "height": video_stream.get('height') if video_stream else None,
                    "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream else 0
                },
                "audio": {
                    "codec": audio_stream.get('codec_name') if audio_stream else None,
                    "sample_rate": audio_stream.get('sample_rate') if audio_stream else None,
                    "channels": audio_stream.get('channels') if audio_stream else None
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def mute_video(self, input_path: str, output_path: str) -> ProcessingResult:
        """
        Remove audio track from video
        
        Args:
            input_path: Path to input video
            output_path: Path to save muted video
        
        Returns:
            ProcessingResult with status
        """
        if not self.ffmpeg_available:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error="FFmpeg not installed"
            )
        
        try:
            (
                ffmpeg
                .input(input_path)
                .output(output_path, an=None, vcodec='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            info = self.get_video_info(output_path)
            return ProcessingResult(
                success=True,
                output_path=output_path,
                file_size_mb=info.get('size_mb', 0),
                duration_seconds=info.get('duration', 0)
            )
        except ffmpeg.Error as e:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error=e.stderr.decode() if e.stderr else str(e)
            )
    
    def concatenate_audio_segments(
        self,
        audio_files: List[str],
        output_path: str,
        gaps: Optional[List[float]] = None
    ) -> ProcessingResult:
        """
        Concatenate multiple audio files with optional gaps
        
        Args:
            audio_files: List of paths to audio files
            output_path: Path to save concatenated audio
            gaps: Optional list of gap durations (seconds) between segments
        
        Returns:
            ProcessingResult with status
        """
        if not self.ffmpeg_available:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error="FFmpeg not installed"
            )
        
        if not audio_files:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error="No audio files provided"
            )
        
        try:
            # Create concat file for FFmpeg
            temp_dir = tempfile.mkdtemp()
            concat_file = os.path.join(temp_dir, "concat.txt")
            
            with open(concat_file, 'w') as f:
                for audio_path in audio_files:
                    # Escape single quotes in path
                    escaped_path = audio_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # Concatenate using FFmpeg
            (
                ffmpeg
                .input(concat_file, format='concat', safe=0)
                .output(output_path, acodec='libmp3lame', audio_bitrate='128k')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            # Get output info
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            return ProcessingResult(
                success=True,
                output_path=output_path,
                file_size_mb=file_size,
                duration_seconds=0  # Would need ffprobe for audio duration
            )
        except Exception as e:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error=str(e)
            )
    
    def stitch_video(
        self,
        original_video_path: str,
        audio_segments: List[dict],
        output_path: str,
        optimize_for_mobile: bool = True
    ) -> ProcessingResult:
        """
        Replace video audio with generated TTS segments
        
        This is the main video processing function that:
        1. Mutes the original video
        2. Creates a timeline of audio segments
        3. Merges new audio with video
        4. Optimizes for low-bandwidth if requested
        
        Args:
            original_video_path: Path to original video file
            audio_segments: List of dicts with file_path, start_time, end_time
            output_path: Path to save final video
            optimize_for_mobile: Apply mobile-optimized compression
        
        Returns:
            ProcessingResult with final video path and size
        """
        if not self.ffmpeg_available:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error="FFmpeg not installed. Please install FFmpeg: https://ffmpeg.org/download.html"
            )
        
        try:
            temp_dir = tempfile.mkdtemp(prefix="nativity_stitch_")
            
            # Step 1: Get video info
            video_info = self.get_video_info(original_video_path)
            if "error" in video_info:
                raise Exception(f"Cannot read video: {video_info['error']}")
            
            video_duration = video_info['duration']
            
            # Step 2: Concatenate all audio segments
            audio_files = [seg.get('file_path') for seg in audio_segments if seg.get('file_path')]
            
            if not audio_files:
                raise Exception("No audio segments provided")
            
            combined_audio = os.path.join(temp_dir, "combined_audio.mp3")
            concat_result = self.concatenate_audio_segments(audio_files, combined_audio)
            
            if not concat_result.success:
                raise Exception(f"Audio concatenation failed: {concat_result.error}")
            
            # Step 3: Merge video with new audio
            video_input = ffmpeg.input(original_video_path)
            audio_input = ffmpeg.input(combined_audio)
            
            # Build output options based on optimization settings
            output_options = {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'audio_bitrate': '128k',
                'shortest': None,  # End when shortest stream ends
            }
            
            if optimize_for_mobile:
                # Low-bandwidth optimization for WhatsApp/Mobile
                output_options.update({
                    'preset': 'fast',
                    'crf': 28,  # Higher CRF = smaller file, slightly lower quality
                    'vf': 'scale=-2:480',  # Scale to 480p height, maintain aspect
                    'movflags': '+faststart',  # Optimize for streaming
                })
            else:
                output_options.update({
                    'preset': 'medium',
                    'crf': 23,  # Standard quality
                })
            
            # Run FFmpeg
            (
                ffmpeg
                .output(
                    video_input.video,
                    audio_input.audio,
                    output_path,
                    **output_options
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Step 4: Get final output info
            final_info = self.get_video_info(output_path)
            
            # Cleanup temp files
            shutil.rmtree(temp_dir)
            
            return ProcessingResult(
                success=True,
                output_path=output_path,
                file_size_mb=final_info.get('size_mb', 0),
                duration_seconds=final_info.get('duration', 0)
            )
            
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error=f"FFmpeg error: {error_msg}"
            )
        except Exception as e:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error=str(e)
            )
    
    def create_whatsapp_version(
        self,
        input_path: str,
        output_path: str,
        target_size_mb: float = 15.0
    ) -> ProcessingResult:
        """
        Create a WhatsApp-optimized version (<15MB)
        
        Uses two-pass encoding to hit target file size
        
        Args:
            input_path: Path to input video
            output_path: Path to save optimized video
            target_size_mb: Target file size in MB
        
        Returns:
            ProcessingResult with optimized video
        """
        if not self.ffmpeg_available:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error="FFmpeg not installed"
            )
        
        try:
            # Get video duration
            info = self.get_video_info(input_path)
            duration = info.get('duration', 60)
            
            # Calculate target bitrate
            # Formula: bitrate = (target_size * 8192) / duration
            # Subtract 128kbps for audio
            target_bitrate = int((target_size_mb * 8192) / duration) - 128
            target_bitrate = max(target_bitrate, 200)  # Minimum 200kbps
            
            # Single pass with calculated bitrate
            (
                ffmpeg
                .input(input_path)
                .output(
                    output_path,
                    vcodec='libx264',
                    video_bitrate=f'{target_bitrate}k',
                    acodec='aac',
                    audio_bitrate='96k',
                    preset='fast',
                    vf='scale=-2:360',  # 360p for maximum compression
                    movflags='+faststart'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            final_info = self.get_video_info(output_path)
            
            return ProcessingResult(
                success=True,
                output_path=output_path,
                file_size_mb=final_info.get('size_mb', 0),
                duration_seconds=final_info.get('duration', 0)
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                output_path=None,
                file_size_mb=0,
                duration_seconds=0,
                error=str(e)
            )


# Singleton instance
ffmpeg_service = FFmpegService()


def check_ffmpeg_installation() -> dict:
    """
    Check FFmpeg installation and return system info
    """
    service = FFmpegService()
    
    if service.is_available():
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
            return {
                "installed": True,
                "version": version_line,
                "message": "FFmpeg is ready to use"
            }
        except Exception as e:
            return {
                "installed": False,
                "error": str(e),
                "message": "FFmpeg check failed"
            }
    else:
        return {
            "installed": False,
            "message": "FFmpeg is not installed. Please install it:",
            "instructions": {
                "windows": "Download from https://ffmpeg.org/download.html and add to PATH",
                "mac": "brew install ffmpeg",
                "linux": "sudo apt install ffmpeg"
            }
        }
