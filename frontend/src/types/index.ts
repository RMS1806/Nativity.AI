// Types for Nativity.ai frontend

export type AppState = 'IDLE' | 'UPLOADING' | 'PROCESSING' | 'COMPLETED' | 'ERROR';

export type JobStatus =
    | 'pending'
    | 'uploading'
    | 'analyzing'
    | 'generating_audio'
    | 'stitching'
    | 'complete'
    | 'needs_review'
    | 'failed';

export interface Language {
    code: string;
    name: string;
    native: string;
}

export interface CulturalAdaptation {
    has_idiom: boolean;
    original_idiom?: string;
    adapted_meaning?: string;
    adaptation_note?: string;
}

export interface VideoSegment {
    id: number;
    start_time: string;
    end_time: string;
    speaker: string;
    original_text: string;
    translated_text: string;
    cultural_adaptation: CulturalAdaptation;
}

export interface CulturalSensitivity {
    timestamp: string;
    description: string;
    recommendation: string;
}

export interface CulturalReport {
    idioms_adapted: number;
    cultural_sensitivities: CulturalSensitivity[];
    localization_quality_score: number;
    notes: string;
}

export interface LocalizationJob {
    job_id: string;
    status: JobStatus;
    progress: number;
    message: string;
    input_file: string;
    target_language: string;
    output_file?: string;
    error?: string;
    results?: {
        output_url?: string;
        whatsapp_url?: string;
        file_size_mb?: number;
        cultural_report?: CulturalReport;
        analysis?: {
            segments: VideoSegment[];
            cultural_report: CulturalReport;
        };
    };
}

export interface UploadResponse {
    upload_url: string;
    file_key: string;
    bucket: string;
    expires_in: number;
}

export interface LocalizationResponse {
    job_id: string;
    status: string;
    message: string;
}
