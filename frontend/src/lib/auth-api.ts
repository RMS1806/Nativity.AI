'use client';

import { useAuth } from '@clerk/nextjs';
import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { useEffect, useMemo, useRef, useState, useCallback } from 'react';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Creates an authenticated Axios instance that includes the Clerk JWT token
 * in the Authorization header for all requests.
 * 
 * Usage:
 * ```tsx
 * function MyComponent() {
 *   const api = useAuthenticatedApi();
 *   
 *   const fetchData = async () => {
 *     const response = await api.get('/api/video/history');
 *     return response.data;
 *   };
 * }
 * ```
 */
export function useAuthenticatedApi(): AxiosInstance {
    const { getToken, isSignedIn } = useAuth();
    const tokenRef = useRef<string | null>(null);

    // Create a base axios instance
    const api = useMemo(() => {
        const instance = axios.create({
            baseURL: API_BASE_URL,
            headers: {
                'Content-Type': 'application/json',
            },
            validateStatus: (status) => status >= 200 && status < 600,
        });

        // Request interceptor to add Authorization header
        instance.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
            console.log('Authenticated API - Calling Backend at:', API_BASE_URL);

            // Get fresh token for each request
            try {
                const token = await getToken();
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                    console.log('Auth token attached to request');
                } else {
                    console.log('No auth token available');
                }
            } catch (error) {
                console.error('Failed to get auth token:', error);
            }

            return config;
        });

        return instance;
    }, [getToken]);

    return api;
}

/**
 * Hook to get just the current token (useful for custom fetch calls)
 */
export function useAuthToken() {
    const { getToken, isSignedIn } = useAuth();

    const fetchToken = async (): Promise<string | null> => {
        if (!isSignedIn) return null;
        try {
            return await getToken();
        } catch {
            return null;
        }
    };

    return { getToken: fetchToken, isSignedIn };
}

/**
 * Video history item from the backend
 */
export interface HistoryVideo {
    job_id: string;
    target_language: string;
    input_file: string;
    status: string;
    created_at: string;
    output_url?: string;
    input_url?: string;
    whatsapp_url?: string;
    file_size_mb?: number;
    segments_count?: number;
    draft_segments?: any[];
    cultural_report?: {
        idioms_adapted?: number;
        cultural_notes?: string[];
    };
}

export interface DashboardStats {
    total_projects: number;
    languages_used: number;
    minutes_saved: number;
}

export interface HistoryResponse {
    success: boolean;
    videos: HistoryVideo[];
    count: number;
    stats?: DashboardStats;
}

/**
 * Hook to fetch user's video history
 * Returns loading state, error, data, and refetch function
 */
export function useHistory() {
    const api = useAuthenticatedApi();
    const { isSignedIn } = useAuth();
    const [data, setData] = useState<HistoryResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchHistory = useCallback(async () => {
        if (!isSignedIn) {
            setData(null);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const response = await api.get('/api/video/history');
            if (response.status === 200) {
                setData(response.data);
            } else if (response.status === 401) {
                setError('Please sign in to view history');
            } else {
                setError(response.data?.detail || 'Failed to fetch history');
            }
        } catch (err: any) {
            setError(err.message || 'Failed to fetch history');
        } finally {
            setLoading(false);
        }
    }, [api, isSignedIn]);

    // Fetch on mount and when auth changes
    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);

    return { data, loading, error, refetch: fetchHistory };
}

// Re-export non-authenticated functions for backwards compatibility
export { getUploadUrl, uploadToS3, getLanguages, healthCheck, getConfigStatus } from './api';
