import axios from 'axios';
import { UploadResponse, LocalizationJob, LocalizationResponse, Language } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    // Accept all status codes to handle errors gracefully
    validateStatus: (status) => status >= 200 && status < 600,
});

// Request interceptor for debugging
api.interceptors.request.use((config) => {
    console.log('Calling Backend at:', api.defaults.baseURL);
    return config;
});

/**
 * Helper to create headers with optional auth token
 */
function createAuthHeaders(token?: string): Record<string, string> {
    const headers: Record<string, string> = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    return headers;
}

// Get presigned URL for S3 upload
export async function getUploadUrl(
    fileName: string,
    contentType: string = 'video/mp4',
    token?: string
): Promise<UploadResponse> {
    const response = await api.post('/api/video/upload-url', {
        file_name: fileName,
        content_type: contentType,
    }, {
        headers: createAuthHeaders(token),
    });
    return response.data;
}

// Upload file directly to S3 using presigned URL
export async function uploadToS3(
    uploadUrl: string,
    file: File,
    onProgress?: (progress: number) => void
): Promise<void> {
    console.log("Uploading to S3 URL:", uploadUrl);
    await axios.put(uploadUrl, file, {
        headers: {
            'Content-Type': file.type,
        },
        onUploadProgress: (progressEvent) => {
            if (progressEvent.total && onProgress) {
                const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(progress);
            }
        },
    });
}

// Start localization job (REQUIRES AUTH TOKEN)
export async function startLocalization(
    fileKey: string,
    targetLanguage: string,
    token?: string
): Promise<LocalizationResponse> {
    const response = await api.post('/api/video/localize', {
        file_key: fileKey,
        target_language: targetLanguage,
    }, {
        headers: createAuthHeaders(token),
    });

    // Handle 401 explicitly
    if (response.status === 401) {
        throw new Error('Authentication required. Please sign in to localize videos.');
    }

    return response.data;
}

// Poll job status
export async function getJobStatus(jobId: string, token?: string): Promise<LocalizationJob> {
    const response = await api.get(`/api/video/job/${jobId}`, {
        headers: createAuthHeaders(token),
    });
    return response.data;
}

// Get supported languages
export async function getLanguages(): Promise<{ languages: Language[] }> {
    const response = await api.get('/api/video/languages');
    return response.data;
}

// Quick translate (for testing)
export async function quickTranslate(text: string, targetLanguage: string) {
    const response = await api.post('/api/video/translate', {
        text,
        target_language: targetLanguage,
    });
    return response.data;
}

// Health check
export async function healthCheck() {
    const response = await api.get('/api/health');
    return response.data;
}

// Config status
export async function getConfigStatus() {
    const response = await api.get('/api/config/status');
    return response.data;
}

export default api;
