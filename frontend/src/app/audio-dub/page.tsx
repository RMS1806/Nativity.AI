'use client';

import { useState, useCallback, useRef } from 'react';
import { useAuth, UserButton } from '@clerk/nextjs';
import { motion } from 'framer-motion';
import {
    Music, Home, LayoutDashboard, Upload, CheckCircle,
    AlertCircle, Loader2, Download, ArrowLeft,
} from 'lucide-react';
import Link from 'next/link';
import axios from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const LANGUAGES = [
    { code: 'hindi',   name: 'Hindi',   native: 'हिंदी' },
    { code: 'tamil',   name: 'Tamil',   native: 'தமிழ்' },
    { code: 'bengali', name: 'Bengali', native: 'বাংলা' },
    { code: 'telugu',  name: 'Telugu',  native: 'తెలుగు' },
    { code: 'marathi', name: 'Marathi', native: 'मराठी' },
];

type Phase = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

interface JobResult {
    status: string;
    progress: number;
    message: string;
    results?: { output_url?: string; dub_audio_url?: string; file_size_mb?: number };
    error?: string;
}

export default function AudioDubPage() {
    const { getToken } = useAuth();
    const [phase, setPhase] = useState<Phase>('idle');
    const [language, setLanguage] = useState('hindi');
    const [uploadProgress, setUploadProgress] = useState(0);
    const [jobResult, setJobResult] = useState<JobResult | null>(null);
    const [errorMsg, setErrorMsg] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const stopPoller = () => {
        if (pollerRef.current) {
            clearInterval(pollerRef.current);
            pollerRef.current = null;
        }
    };

    const pollJob = useCallback((jobId: string) => {
        stopPoller();
        pollerRef.current = setInterval(async () => {
            try {
                const res = await axios.get(`${API_BASE}/api/video/job/${jobId}`);
                const data: JobResult = res.data;
                setJobResult(data);
                if (data.status === 'complete') {
                    stopPoller();
                    setPhase('done');
                } else if (data.status === 'failed') {
                    stopPoller();
                    setErrorMsg(data.message || data.error || 'Job failed');
                    setPhase('error');
                }
            } catch (e) {
                console.error('Poll error', e);
            }
        }, 3000);
    }, []);

    const handleFile = useCallback(async (file: File) => {
        if (!file.type.startsWith('video/')) {
            setErrorMsg('Please select a video file.');
            setPhase('error');
            return;
        }

        setPhase('uploading');
        setUploadProgress(0);
        setJobResult(null);
        setErrorMsg('');

        try {
            const token = await getToken();

            // 1. Get presigned URL
            const urlRes = await axios.post(`${API_BASE}/api/video/upload-url`, {
                file_name: file.name,
                content_type: file.type,
            });
            const { upload_url, file_key } = urlRes.data;

            // 2. Upload directly to S3
            await axios.put(upload_url, file, {
                headers: { 'Content-Type': file.type },
                onUploadProgress: (e) => {
                    if (e.total) setUploadProgress(Math.round((e.loaded / e.total) * 100));
                },
            });

            setUploadProgress(100);
            setPhase('processing');

            // 3. Start audio-only localization
            const jobRes = await axios.post(
                `${API_BASE}/api/video/localize-audio`,
                { file_key, target_language: language },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const { job_id } = jobRes.data;

            setJobResult({ status: 'pending', progress: 5, message: 'Starting…' });
            pollJob(job_id);

        } catch (e: any) {
            console.error(e);
            setErrorMsg(e?.response?.data?.detail || e?.message || 'Something went wrong');
            setPhase('error');
        }
    }, [language, getToken, pollJob]);

    const onDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            const file = e.dataTransfer.files[0];
            if (file) handleFile(file);
        },
        [handleFile]
    );

    const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    };

    const reset = () => {
        stopPoller();
        setPhase('idle');
        setJobResult(null);
        setErrorMsg('');
        setUploadProgress(0);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    const audioUrl = jobResult?.results?.dub_audio_url || jobResult?.results?.output_url;

    return (
        <div className="min-h-screen flex" style={{ backgroundColor: '#f4ede5' }}>
            {/* ── Sidebar ─────────────────────────────────────────────── */}
            <aside
                className="hidden lg:flex flex-col w-64 p-6 shrink-0"
                style={{ borderRight: '3px solid #1A1A1A', backgroundColor: '#fff' }}
            >
                <div className="mb-6 mt-2 px-4">
                    <h1 className="text-xl font-bold font-headline text-[#1A1A1A]">Creator Studio</h1>
                    <p className="font-mono-label text-[#5c403d] mt-1">Localization Hub</p>
                </div>
                <nav className="flex-1 space-y-2">
                    <Link
                        href="/"
                        className="flex items-center gap-3 px-4 py-3 font-mono-label text-[#1A1A1A] hover:bg-[#eee7df] hover:translate-x-1 transition-all"
                    >
                        <Home className="w-5 h-5" />
                        Home
                    </Link>
                    <Link
                        href="/dashboard"
                        className="flex items-center gap-3 px-4 py-3 font-mono-label text-[#1A1A1A] hover:bg-[#eee7df] hover:translate-x-1 transition-all"
                    >
                        <LayoutDashboard className="w-5 h-5" />
                        Dashboard
                    </Link>
                    <div
                        className="flex items-center gap-3 px-4 py-3 font-mono-label text-white neo-border"
                        style={{
                            backgroundColor: '#9c48ea',
                            boxShadow: '4px 4px 0px 0px #1A1A1A',
                        }}
                    >
                        <Music className="w-5 h-5" />
                        Audio Dub
                    </div>
                </nav>
                <div className="mt-auto pt-4" style={{ borderTop: '3px solid #1A1A1A' }}>
                    <UserButton afterSignOutUrl="/" />
                </div>
            </aside>

            {/* ── Main content ─────────────────────────────────────────── */}
            <main className="flex-1 p-6 lg:p-10 max-w-2xl mx-auto">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 neo-border" style={{ backgroundColor: '#9c48ea' }}>
                            <Music className="w-6 h-6 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold font-headline text-[#1A1A1A]">Audio Dub</h2>
                    </div>
                    <p className="font-mono-label text-[#5c403d] text-sm">
                        Upload any video — we extract the audio, dub it, and return a .aac file
                        ready for YouTube Studio. No length limit. No video encode.
                    </p>
                </motion.div>

                {/* Language Selector */}
                {phase === 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 }}
                        className="mb-6"
                    >
                        <label className="block font-mono-label text-xs uppercase tracking-wider text-[#5c403d] mb-2">
                            Target Language
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {LANGUAGES.map((l) => (
                                <button
                                    key={l.code}
                                    onClick={() => setLanguage(l.code)}
                                    className={`px-4 py-2 font-mono-label text-sm neo-border transition-all ${
                                        language === l.code
                                            ? 'text-white'
                                            : 'bg-white text-[#1A1A1A] hover:bg-[#eee7df]'
                                    }`}
                                    style={
                                        language === l.code
                                            ? { backgroundColor: '#9c48ea', boxShadow: '3px 3px 0 #1A1A1A' }
                                            : {}
                                    }
                                >
                                    {l.name} · {l.native}
                                </button>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Upload Zone */}
                {phase === 'idle' && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        onDrop={onDrop}
                        onDragOver={(e) => e.preventDefault()}
                        onClick={() => fileInputRef.current?.click()}
                        className="cursor-pointer neo-border neo-shadow p-12 flex flex-col items-center gap-4 bg-white hover:bg-[#eee7df] transition-all"
                    >
                        <Upload className="w-10 h-10 text-[#5c403d]" />
                        <p className="font-mono-label text-[#1A1A1A] text-center">
                            Drag &amp; drop a video, or <span className="underline">browse</span>
                        </p>
                        <p className="font-mono-label text-xs text-[#5c403d]">
                            MP4, MOV, MKV, AVI — any length
                        </p>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="video/*"
                            className="hidden"
                            onChange={onInputChange}
                        />
                    </motion.div>
                )}

                {/* Uploading */}
                {phase === 'uploading' && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="neo-border neo-shadow p-8 bg-white"
                    >
                        <p className="font-mono-label text-[#1A1A1A] mb-4">Uploading video…</p>
                        <div className="w-full neo-border h-4 bg-[#eee7df] overflow-hidden">
                            <div
                                className="h-full transition-all"
                                style={{ width: `${uploadProgress}%`, backgroundColor: '#9c48ea' }}
                            />
                        </div>
                        <p className="font-mono-label text-xs text-[#5c403d] mt-2 text-right">
                            {uploadProgress}%
                        </p>
                    </motion.div>
                )}

                {/* Processing */}
                {phase === 'processing' && jobResult && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="neo-border neo-shadow p-8 bg-white"
                    >
                        <div className="flex items-center gap-3 mb-4">
                            <Loader2 className="w-5 h-5 animate-spin text-[#9c48ea]" />
                            <p className="font-mono-label text-[#1A1A1A]">{jobResult.message}</p>
                        </div>
                        <div className="w-full neo-border h-4 bg-[#eee7df] overflow-hidden">
                            <div
                                className="h-full transition-all duration-700"
                                style={{ width: `${jobResult.progress}%`, backgroundColor: '#9c48ea' }}
                            />
                        </div>
                        <p className="font-mono-label text-xs text-[#5c403d] mt-2 text-right">
                            {jobResult.progress}%
                        </p>
                    </motion.div>
                )}

                {/* Done */}
                {phase === 'done' && (
                    <motion.div
                        initial={{ opacity: 0, y: 12 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="neo-border neo-shadow p-8 bg-white"
                    >
                        <div className="flex items-center gap-3 mb-6">
                            <CheckCircle className="w-6 h-6 text-green-600" />
                            <p className="font-headline text-xl font-bold text-[#1A1A1A]">Dub Ready!</p>
                        </div>

                        {jobResult?.results?.file_size_mb && (
                            <p className="font-mono-label text-sm text-[#5c403d] mb-4">
                                File size: {jobResult.results.file_size_mb.toFixed(1)} MB
                            </p>
                        )}

                        <p className="font-mono-label text-xs text-[#5c403d] mb-6">
                            Upload this .aac file to YouTube Studio → Audio → Add audio track
                            to let viewers switch between Original and dubbed audio.
                        </p>

                        {audioUrl ? (
                            <a
                                href={audioUrl}
                                download
                                className="flex items-center justify-center gap-2 py-4 px-6 font-mono-label font-bold uppercase tracking-wider neo-border neo-shadow neo-shadow-hover neo-shadow-active transition-all text-white"
                                style={{ backgroundColor: '#9c48ea' }}
                            >
                                <Download className="w-5 h-5" />
                                Download Dubbed Audio (.aac)
                            </a>
                        ) : (
                            <p className="font-mono-label text-sm text-red-600">
                                Download URL not available — check Render logs.
                            </p>
                        )}

                        <button
                            onClick={reset}
                            className="mt-4 w-full flex items-center justify-center gap-2 py-3 font-mono-label text-[#1A1A1A] neo-border bg-white hover:bg-[#eee7df] transition-all"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Dub Another Video
                        </button>
                    </motion.div>
                )}

                {/* Error */}
                {phase === 'error' && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="neo-border neo-shadow p-8 bg-white"
                    >
                        <div className="flex items-center gap-3 mb-4">
                            <AlertCircle className="w-6 h-6 text-red-600" />
                            <p className="font-headline text-lg font-bold text-[#1A1A1A]">Something went wrong</p>
                        </div>
                        <p className="font-mono-label text-sm text-[#5c403d] mb-6">{errorMsg}</p>
                        <button
                            onClick={reset}
                            className="flex items-center gap-2 py-3 px-6 font-mono-label neo-border bg-white hover:bg-[#eee7df] transition-all"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Try Again
                        </button>
                    </motion.div>
                )}
            </main>
        </div>
    );
}
