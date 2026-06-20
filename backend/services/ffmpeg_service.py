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

    @staticmethod
    def _parse_timestamp(val) -> float:
        """Convert a timestamp to float seconds.

        Accepts numbers (already seconds) or strings like 'SS', 'MM:SS',
        or 'HH:MM:SS' (Gemini returns 'MM:SS').
        """
        if isinstance(val, (int, float)):
            return float(val)
        try:
            parts = [float(p) for p in str(val).strip().split(":")]
        except (ValueError, AttributeError):
            return 0.0
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return 0.0

    def _get_audio_duration_seconds(self, path: str) -> float:
        """Return the duration of an audio file in seconds (0.0 on failure)."""
        try:
            probe = ffmpeg.probe(path)
            return float(probe['format'].get('duration', 0.0))
        except Exception:
            return 0.0

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
        optimize_for_mobile: bool = True,
        background_volume: float = 0.15,
        tts_volume: float = 1.0,
        tts_delay_seconds: float = 0.0
    ) -> ProcessingResult:
        """
        Mix original video audio (background) with generated TTS audio
        
        This is the main video processing function that:
        1. Gets video info and checks for original audio stream
        2. Creates a timeline of TTS audio segments
        3. DELAYS TTS to match first spoken word (intro music preservation)
        4. MIXES original audio (lowered) with TTS audio (full volume)
        5. Keeps FULL video duration (no abrupt cuts)
        6. Falls back to simple replacement if no original audio exists
        
        Args:
            original_video_path: Path to original video file
            audio_segments: List of dicts with file_path, start_time, end_time
            output_path: Path to save final video
            optimize_for_mobile: Apply mobile-optimized compression
            background_volume: Volume level for original background audio (0.0-1.0, default 0.15 = 15%)
            tts_volume: Volume level for TTS voiceover (0.0-1.0, default 1.0 = 100%)
            tts_delay_seconds: Delay TTS audio by this many seconds to match first spoken word (default 0.0)
        
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
            
            # Check if original video has an audio stream
            has_original_audio = video_info.get('audio', {}).get('codec') is not None
            print(f"🎵 Original video has audio: {has_original_audio}")
            
            # ─────────────────────────────────────────────────────────────
            # Step 2: Build a TIME-ALIGNED dub track.
            # For each segment we (a) speed it up (atempo) so it fits its
            # original spoken time slot, and (b) place it at its real start
            # timestamp (adelay). This keeps the dub in sync with the speaker
            # instead of concatenating back-to-back and drifting past the end.
            # ─────────────────────────────────────────────────────────────
            valid_segments = [
                s for s in audio_segments
                if s.get('file_path') and os.path.exists(s.get('file_path'))
            ]
            if not valid_segments:
                raise Exception("No audio segments provided")

            MAX_TEMPO = 2.0  # strict-sync cap (single atempo filter max is 2.0x)

            inputs = ["-i", original_video_path]
            filter_parts = []
            seg_labels = []

            for idx, seg in enumerate(valid_segments):
                file_path = seg['file_path']
                start_s = self._parse_timestamp(seg.get('start_time', 0))
                end_s = self._parse_timestamp(seg.get('end_time', 0))
                slot_s = max(end_s - start_s, 0.0)
                gen_s = self._get_audio_duration_seconds(file_path)

                # Speed up to fit the slot (strict sync); never slow down below 1.0x
                tempo = 1.0
                if slot_s > 0 and gen_s > slot_s:
                    tempo = min(gen_s / slot_s, MAX_TEMPO)

                input_index = idx + 1  # input 0 is the video
                inputs += ["-i", file_path]

                delay_ms = max(int(round(start_s * 1000)), 0)
                label = f"s{input_index}"
                # volume -> time-stretch (pitch-preserving) -> place at start time
                filter_parts.append(
                    f"[{input_index}:a]volume={tts_volume},atempo={tempo:.4f},"
                    f"adelay={delay_ms}|{delay_ms}[{label}]"
                )
                seg_labels.append(f"[{label}]")

            print(
                f"🎙️ Time-aligning {len(valid_segments)} segments "
                f"(strict sync, max {MAX_TEMPO}x), bg audio={has_original_audio}"
            )

            # Lowered original audio as a background bed (if present)
            mix_inputs = list(seg_labels)
            if has_original_audio:
                filter_parts.append(f"[0:a]volume={background_volume}[bg]")
                mix_inputs.append("[bg]")

            # Mix everything, then trim to the video length so audio never
            # runs past the end of the video.
            if len(mix_inputs) > 1:
                filter_parts.append(
                    f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:"
                    f"duration=longest:normalize=0[mixed]"
                )
                mixed_label = "[mixed]"
            else:
                mixed_label = mix_inputs[0]

            filter_parts.append(
                f"{mixed_label}atrim=0:{video_duration:.3f},asetpts=PTS-STARTPTS[aout]"
            )

            filter_complex = ";".join(filter_parts)

            cmd = ["ffmpeg", "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
            ]

            if optimize_for_mobile:
                cmd += [
                    "-c:v", "libx264", "-preset", "fast", "-crf", "28",
                    "-vf", "scale=-2:480", "-movflags", "+faststart",
                ]
            else:
                cmd += ["-c:v", "copy"]

            cmd += ["-c:a", "aac", "-b:a", "128k", output_path]

            print("🎬 Running FFmpeg (time-aligned dub)...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"FFmpeg stitching failed: {result.stderr[-2000:]}")

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
