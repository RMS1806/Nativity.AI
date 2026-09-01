"""
FFmpeg Service for Nativity.ai
Handles video processing, audio stitching, and optimization

Uses ffmpeg-python for programmatic control of FFmpeg
"""

import ffmpeg
import math
import subprocess
import os
import shutil
import tempfile
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Chunked FFmpeg constants — keeps peak RAM low on Render free tier
_BATCH_THRESHOLD = 20   # above this many segments, use chunked mode
_CHUNK_WINDOW_S  = 90.0 # seconds per rendering window in chunked mode


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
        Mix original video audio (background) with generated TTS audio.

        Routes to single-pass mode (≤ _BATCH_THRESHOLD segments) or chunked
        mode (> _BATCH_THRESHOLD segments) to keep peak RAM predictable on
        Render free tier.
        """
        if not self.ffmpeg_available:
            return ProcessingResult(
                success=False, output_path=None, file_size_mb=0,
                duration_seconds=0,
                error="FFmpeg not installed. Please install FFmpeg: https://ffmpeg.org/download.html"
            )

        try:
            video_info = self.get_video_info(original_video_path)
            if "error" in video_info:
                raise Exception(f"Cannot read video: {video_info['error']}")

            video_duration = video_info['duration']
            has_original_audio = video_info.get('audio', {}).get('codec') is not None
            print(f"🎵 Original video has audio: {has_original_audio}")

            valid_segments = [
                s for s in audio_segments
                if s.get('file_path') and os.path.exists(s.get('file_path'))
            ]
            if not valid_segments:
                raise Exception("No audio segments provided")

            mode = "chunked" if len(valid_segments) > _BATCH_THRESHOLD else "single-pass"
            print(f"🎬 Stitch: {len(valid_segments)} segments → {mode} mode")

            if mode == "chunked":
                return self._stitch_chunked(
                    original_video_path=original_video_path,
                    valid_segments=valid_segments,
                    output_path=output_path,
                    video_duration=video_duration,
                    has_original_audio=has_original_audio,
                    optimize_for_mobile=optimize_for_mobile,
                    background_volume=background_volume,
                    tts_volume=tts_volume,
                )
            else:
                return self._stitch_single_pass(
                    original_video_path=original_video_path,
                    valid_segments=valid_segments,
                    output_path=output_path,
                    video_duration=video_duration,
                    has_original_audio=has_original_audio,
                    optimize_for_mobile=optimize_for_mobile,
                    background_volume=background_volume,
                    tts_volume=tts_volume,
                )

        except ffmpeg.Error as e:
            return ProcessingResult(
                success=False, output_path=None, file_size_mb=0, duration_seconds=0,
                error=f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}"
            )
        except Exception as e:
            return ProcessingResult(
                success=False, output_path=None, file_size_mb=0,
                duration_seconds=0, error=str(e)
            )

    def _build_duck_filter(self, segments: list, background_volume: float,
                           in_label: str = "0:a", out_label: str = "bg") -> str:
        """
        Build a time-varying volume filter that ducks the original audio only
        during speech segments. Full volume in gaps → natural game/music sound;
        ducked to background_volume during TTS speech → dub is clear.
        A 0.1s pre-buffer and 0.25s post-buffer smooth the transitions.
        """
        if not segments:
            return f"[{in_label}]volume=1.0[{out_label}]"

        duck_parts = []
        for seg in segments:
            s = max(0.0, self._parse_timestamp(seg.get('start_time', 0)) - 0.1)
            e = self._parse_timestamp(seg.get('end_time', 0)) + 0.25
            duck_parts.append(f"between(t,{s:.3f},{e:.3f})")

        duck_expr = "+".join(duck_parts)
        vol_expr = f"if(gt({duck_expr},0),{background_volume},1.0)"
        return f"[{in_label}]volume='{vol_expr}':eval=frame[{out_label}]"

    def _stitch_single_pass(
        self, original_video_path, valid_segments, output_path,
        video_duration, has_original_audio, optimize_for_mobile,
        background_volume, tts_volume
    ) -> ProcessingResult:
        """Single filter_complex pass — used when segment count is small."""
        MAX_TEMPO = 2.0
        inputs = ["-i", original_video_path]
        filter_parts = []
        seg_labels = []

        for idx, seg in enumerate(valid_segments):
            file_path = seg['file_path']
            start_s = self._parse_timestamp(seg.get('start_time', 0))
            end_s = self._parse_timestamp(seg.get('end_time', 0))
            slot_s = max(end_s - start_s, 0.0)
            gen_s = self._get_audio_duration_seconds(file_path)

            tempo = 1.0
            if slot_s > 0 and gen_s > slot_s:
                tempo = min(gen_s / slot_s, MAX_TEMPO)

            input_index = idx + 1
            inputs += ["-i", file_path]
            delay_ms = max(int(round(start_s * 1000)), 0)
            label = f"s{input_index}"
            filter_parts.append(
                f"[{input_index}:a]volume={tts_volume},atempo={tempo:.4f},"
                f"adelay={delay_ms}|{delay_ms}[{label}]"
            )
            seg_labels.append(f"[{label}]")

        print(f"🎙️ Time-aligning {len(valid_segments)} segments (max {MAX_TEMPO}x)")

        mix_inputs = list(seg_labels)
        if has_original_audio:
            filter_parts.append(self._build_duck_filter(valid_segments, background_volume))
            mix_inputs.append("[bg]")

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

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "0:v", "-map", "[aout]",
        ]
        if optimize_for_mobile:
            # ultrafast for short clips — quality gap vs fast is negligible; speed is 3-5×
            preset = "ultrafast" if video_duration <= 120 else "fast"
            cmd += ["-c:v", "libx264", "-preset", preset, "-crf", "28",
                    "-vf", "scale=-2:480", "-movflags", "+faststart"]
        else:
            cmd += ["-c:v", "copy"]
        cmd += ["-c:a", "aac", "-b:a", "128k", output_path]

        print(f"🎬 Running FFmpeg (single-pass, preset={preset if optimize_for_mobile else 'copy'}, dur={video_duration:.0f}s)...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise Exception(f"FFmpeg stitching failed: {result.stderr[-2000:]}")

        info = self.get_video_info(output_path)
        return ProcessingResult(
            success=True, output_path=output_path,
            file_size_mb=info.get('size_mb', 0),
            duration_seconds=info.get('duration', 0)
        )

    def _render_tts_window(
        self, window_segs: list, t_start: float, window_dur: float,
        tts_volume: float, output_path: str
    ):
        """
        Render TTS audio for one time window to an AAC file.
        Segment delays are relative to t_start. Original audio is NOT mixed here
        (handled later in the final mux so only one amix is ever needed).
        """
        MAX_TEMPO = 2.0

        if not window_segs:
            # No speech in this window — output silence
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", f"{window_dur:.3f}",
                "-c:a", "aac", "-b:a", "128k",
                output_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if result.returncode != 0:
                raise Exception(f"FFmpeg silence gen failed: {result.stderr[-500:]}")
            return

        inputs = []
        filter_parts = []
        seg_labels = []

        for idx, seg in enumerate(window_segs):
            file_path = seg['file_path']
            start_s = self._parse_timestamp(seg.get('start_time', 0))
            end_s = self._parse_timestamp(seg.get('end_time', 0))
            slot_s = max(end_s - start_s, 0.0)
            gen_s = self._get_audio_duration_seconds(file_path)

            tempo = 1.0
            if slot_s > 0 and gen_s > slot_s:
                tempo = min(gen_s / slot_s, MAX_TEMPO)

            inputs += ["-i", file_path]
            delay_ms = max(int(round((start_s - t_start) * 1000)), 0)
            label = f"s{idx}"
            filter_parts.append(
                f"[{idx}:a]volume={tts_volume},atempo={tempo:.4f},"
                f"adelay={delay_ms}|{delay_ms}[{label}]"
            )
            seg_labels.append(f"[{label}]")

        if len(seg_labels) > 1:
            filter_parts.append(
                f"{''.join(seg_labels)}amix=inputs={len(seg_labels)}:"
                f"duration=longest:normalize=0[mixed]"
            )
            mixed_label = "[mixed]"
        else:
            mixed_label = seg_labels[0]

        filter_parts.append(
            f"{mixed_label}atrim=0:{window_dur:.3f},asetpts=PTS-STARTPTS[aout]"
        )

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", ";".join(filter_parts),
            "-map", "[aout]",
            "-c:a", "aac", "-b:a", "128k",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise Exception(
                f"FFmpeg window render failed (t={t_start:.0f}s): {result.stderr[-1000:]}"
            )

    def _stitch_chunked(
        self, original_video_path, valid_segments, output_path,
        video_duration, has_original_audio, optimize_for_mobile,
        background_volume, tts_volume
    ) -> ProcessingResult:
        """
        Chunked FFmpeg path for large segment counts.

        1. Divide video into _CHUNK_WINDOW_S windows.
        2. Render TTS audio for each window (small filter_complex, low RAM).
        3. Concat all window chunks into one full-length TTS track.
        4. Final mux: video + TTS track + original audio background (simple 2-input amix).
        """
        temp_dir = tempfile.mkdtemp(prefix="nativity_chunks_")
        try:
            n_windows = math.ceil(video_duration / _CHUNK_WINDOW_S)
            chunk_paths = []

            print(f"🎬 Chunked mode: {n_windows} windows of {_CHUNK_WINDOW_S:.0f}s each")

            for i in range(n_windows):
                t_start = i * _CHUNK_WINDOW_S
                t_end = min((i + 1) * _CHUNK_WINDOW_S, video_duration)
                window_dur = t_end - t_start

                window_segs = [
                    s for s in valid_segments
                    if t_start <= self._parse_timestamp(s.get('start_time', 0)) < t_end
                ]

                chunk_path = os.path.join(temp_dir, f"chunk_{i:04d}.aac")
                print(f"  Window {i}: [{t_start:.0f}s–{t_end:.0f}s] {len(window_segs)} segs")
                self._render_tts_window(window_segs, t_start, window_dur, tts_volume, chunk_path)
                chunk_paths.append(chunk_path)

            # Concat all window chunks into one full TTS track
            tts_full = os.path.join(temp_dir, "tts_full.aac")
            concat_txt = os.path.join(temp_dir, "concat.txt")
            with open(concat_txt, "w") as f:
                for cp in chunk_paths:
                    f.write(f"file '{cp.replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'\n")

            cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                   "-i", concat_txt, "-c:a", "aac", "-b:a", "128k", tts_full]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if result.returncode != 0:
                raise Exception(f"FFmpeg concat failed: {result.stderr[-1000:]}")

            # Final mux: original video + TTS track, mix with original audio at bg_vol
            cmd = ["ffmpeg", "-y", "-i", original_video_path, "-i", tts_full]

            if has_original_audio:
                duck_filter = self._build_duck_filter(
                    valid_segments, background_volume, in_label="0:a", out_label="bg"
                )
                fc = (
                    f"{duck_filter};"
                    f"[bg][1:a]amix=inputs=2:duration=first:normalize=0[aout]"
                )
                cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]"]
            else:
                cmd += ["-map", "0:v", "-map", "1:a"]

            if optimize_for_mobile:
                preset = "ultrafast" if video_duration <= 120 else "fast"
                cmd += ["-c:v", "libx264", "-preset", preset, "-crf", "28",
                        "-vf", "scale=-2:480", "-movflags", "+faststart"]
            else:
                cmd += ["-c:v", "copy"]

            cmd += ["-c:a", "aac", "-b:a", "128k", output_path]

            print(f"🎬 Running final mux (preset={preset if optimize_for_mobile else 'copy'}, dur={video_duration:.0f}s)...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            if result.returncode != 0:
                raise Exception(f"FFmpeg final mux failed: {result.stderr[-2000:]}")

            info = self.get_video_info(output_path)
            return ProcessingResult(
                success=True, output_path=output_path,
                file_size_mb=info.get('size_mb', 0),
                duration_seconds=info.get('duration', 0)
            )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
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
