/**
 * SRT Subtitle Utilities
 * Converts Gemini JSON segments to standard SRT subtitle format
 */

export interface Segment {
    id?: number;
    start_time: string;
    end_time: string;
    translated_text?: string;
    original_text?: string;
}

/**
 * Convert time string (MM:SS or HH:MM:SS) to seconds
 */
function timeToSeconds(time: string): number {
    const parts = time.split(':').map(p => parseInt(p, 10));

    if (parts.length === 2) {
        // MM:SS format
        return parts[0] * 60 + parts[1];
    }
    if (parts.length === 3) {
        // HH:MM:SS format
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
}

/**
 * Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
 */
function secondsToSrtTime(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.round((seconds % 1) * 1000);

    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

/**
 * Convert Gemini JSON segments to SRT subtitle format
 * 
 * @param segments - Array of segments from Gemini analysis
 * @returns SRT formatted string
 * 
 * @example
 * const srt = jsonToSrt(segments);
 * // Output:
 * // 1
 * // 00:00:01,000 --> 00:00:04,000
 * // नमस्ते, यह पहला सबटाइटल है
 * //
 * // 2
 * // 00:00:05,000 --> 00:00:08,000
 * // यह दूसरा सबटाइटल है
 */
export function jsonToSrt(segments: Segment[]): string {
    if (!segments || segments.length === 0) {
        return '';
    }

    return segments
        .map((seg, index) => {
            const startSeconds = timeToSeconds(seg.start_time);
            const endSeconds = timeToSeconds(seg.end_time);
            const text = seg.translated_text || seg.original_text || '';

            // SRT format: index, timestamp line, text, blank line
            return `${index + 1}\n${secondsToSrtTime(startSeconds)} --> ${secondsToSrtTime(endSeconds)}\n${text}\n`;
        })
        .join('\n');
}

/**
 * Trigger a browser download of SRT content
 * 
 * @param segments - Array of segments from Gemini analysis
 * @param fileName - Base filename (without extension)
 */
export function downloadSrt(segments: Segment[], fileName: string): void {
    const srtContent = jsonToSrt(segments);

    if (!srtContent) {
        console.warn('No segments to convert to SRT');
        return;
    }

    // Create blob and download
    const blob = new Blob([srtContent], { type: 'text/srt;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = fileName.replace(/\.[^/.]+$/, '') + '.srt';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Cleanup
    URL.revokeObjectURL(url);
}

/**
 * Convert segments to VTT format (WebVTT - alternative subtitle format)
 * 
 * @param segments - Array of segments from Gemini analysis
 * @returns VTT formatted string
 */
export function jsonToVtt(segments: Segment[]): string {
    if (!segments || segments.length === 0) {
        return '';
    }

    const vttLines = ['WEBVTT', ''];

    segments.forEach((seg, index) => {
        const startSeconds = timeToSeconds(seg.start_time);
        const endSeconds = timeToSeconds(seg.end_time);
        const text = seg.translated_text || seg.original_text || '';

        // VTT uses dot instead of comma for milliseconds
        const startTime = secondsToSrtTime(startSeconds).replace(',', '.');
        const endTime = secondsToSrtTime(endSeconds).replace(',', '.');

        vttLines.push(`${index + 1}`);
        vttLines.push(`${startTime} --> ${endTime}`);
        vttLines.push(text);
        vttLines.push('');
    });

    return vttLines.join('\n');
}

/**
 * Trigger a browser download of VTT content
 * 
 * @param segments - Array of segments from Gemini analysis
 * @param fileName - Base filename (without extension)
 */
export function downloadVtt(segments: Segment[], fileName: string): void {
    const vttContent = jsonToVtt(segments);

    if (!vttContent) {
        console.warn('No segments to convert to VTT');
        return;
    }

    const blob = new Blob([vttContent], { type: 'text/vtt;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = fileName.replace(/\.[^/.]+$/, '') + '.vtt';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    URL.revokeObjectURL(url);
}
