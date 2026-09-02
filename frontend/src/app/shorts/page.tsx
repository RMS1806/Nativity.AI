'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth, UserButton } from '@clerk/nextjs';
import { motion } from 'framer-motion';
import {
    Scissors, Home, LayoutDashboard, Music,
    Loader2, Download, ChevronLeft, Trash2, Film,
    AlertCircle, RefreshCw,
} from 'lucide-react';
import Link from 'next/link';
import { useAuthenticatedApi, ShortsSource, ShortClip } from '@/lib/auth-api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const LANGUAGE_NAMES: Record<string, string> = {
    hindi: 'Hindi', tamil: 'Tamil', bengali: 'Bengali',
    telugu: 'Telugu', marathi: 'Marathi',
};

function formatDuration(startS: number, endS: number): string {
    const dur = Math.round(endS - startS);
    const m = Math.floor(dur / 60);
    const s = dur % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function SourceCard({
    source,
    onSelect,
}: {
    source: ShortsSource;
    onSelect: () => void;
}) {
    const fileName = (source.input_file || '').split('/').pop() || 'Video';
    const lang = LANGUAGE_NAMES[source.target_language] || source.target_language;

    return (
        <motion.div
            whileHover={{ y: -4, x: -2 }}
            onClick={onSelect}
            className="p-5 bg-white neo-border cursor-pointer transition-all"
            style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}
        >
            <div className="flex items-start gap-4">
                <div
                    className="w-12 h-12 neo-border flex items-center justify-center shrink-0"
                    style={{ backgroundColor: '#F3EDFF' }}
                >
                    <Film className="w-6 h-6 text-[#8127cf]" />
                </div>
                <div className="min-w-0 flex-1">
                    <h3 className="font-bold text-[#1A1A1A] truncate font-headline">{fileName}</h3>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span
                            className="px-2 py-0.5 font-mono-label text-[11px] neo-border text-white font-bold"
                            style={{ backgroundColor: '#8127cf', borderRadius: '9999px' }}
                        >
                            {lang}
                        </span>
                        <span className="font-mono-label text-xs text-[#5c403d]">
                            {source.shorts_count} clip{source.shorts_count !== 1 ? 's' : ''}
                        </span>
                    </div>
                </div>
                <ChevronLeft className="w-4 h-4 text-[#5c403d] rotate-180 shrink-0 mt-1" />
            </div>
        </motion.div>
    );
}

function ClipCard({
    clip,
    onDelete,
}: {
    clip: ShortClip;
    onDelete: (id: string) => void;
}) {
    const [deleting, setDeleting] = useState(false);
    const api = useAuthenticatedApi();

    const handleDelete = async () => {
        setDeleting(true);
        try {
            await api.delete(`/api/shorts/${clip.short_id}`);
            onDelete(clip.short_id);
        } catch {
            setDeleting(false);
        }
    };

    const duration = formatDuration(clip.start_time_s, clip.end_time_s);

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ y: -2 }}
            className="p-4 bg-white neo-border transition-all"
            style={{ boxShadow: '3px 3px 0px 0px #1A1A1A' }}
        >
            <div className="flex items-start gap-3">
                <div
                    className="w-10 h-10 neo-border flex items-center justify-center shrink-0 mt-0.5"
                    style={{ backgroundColor: '#eee7df' }}
                >
                    <Scissors className="w-4 h-4 text-[#5c403d]" />
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-[#1A1A1A] text-sm truncate">{clip.title}</h4>
                    <p className="font-mono-label text-xs text-[#5c403d] mt-0.5">
                        {clip.start_time_s.toFixed(1)}s – {clip.end_time_s.toFixed(1)}s · {duration}
                    </p>
                    {clip.description && (
                        <p className="text-xs text-[#906f6c] mt-1 line-clamp-2">{clip.description}</p>
                    )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    {clip.clip_url && (
                        <motion.a
                            href={clip.clip_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            whileHover={{ y: -2 }}
                            whileTap={{ y: 1 }}
                            className="w-8 h-8 flex items-center justify-center neo-border bg-white text-[#1A1A1A] hover:bg-[#eee7df] transition-colors"
                            style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                            title="Download clip"
                        >
                            <Download className="w-4 h-4" />
                        </motion.a>
                    )}
                    <motion.button
                        onClick={handleDelete}
                        disabled={deleting}
                        whileHover={{ y: -2 }}
                        whileTap={{ y: 1 }}
                        className="w-8 h-8 flex items-center justify-center neo-border bg-white text-[#1A1A1A] hover:bg-[#FF2D78] hover:text-white transition-colors disabled:opacity-50"
                        style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                        title="Delete clip"
                    >
                        {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    </motion.button>
                </div>
            </div>
        </motion.div>
    );
}

export default function ShortsPage() {
    const api = useAuthenticatedApi();

    const [sources, setSources] = useState<ShortsSource[]>([]);
    const [loadingSources, setLoadingSources] = useState(true);
    const [sourcesError, setSourcesError] = useState('');

    const [selectedSource, setSelectedSource] = useState<ShortsSource | null>(null);
    const [clips, setClips] = useState<ShortClip[]>([]);
    const [loadingClips, setLoadingClips] = useState(false);
    const [clipsError, setClipsError] = useState('');

    const fetchSources = useCallback(async () => {
        setLoadingSources(true);
        setSourcesError('');
        try {
            const res = await api.get('/api/shorts/sources');
            setSources(res.data?.sources || []);
        } catch {
            setSourcesError('Failed to load sources');
        } finally {
            setLoadingSources(false);
        }
    }, [api]);

    const fetchClips = useCallback(async (sourceJobId: string) => {
        setLoadingClips(true);
        setClipsError('');
        try {
            const res = await api.get(`/api/shorts/source/${sourceJobId}`);
            setClips(res.data?.shorts || []);
        } catch {
            setClipsError('Failed to load clips');
        } finally {
            setLoadingClips(false);
        }
    }, [api]);

    useEffect(() => { fetchSources(); }, [fetchSources]);

    const handleSelectSource = (source: ShortsSource) => {
        setSelectedSource(source);
        setClips([]);
        fetchClips(source.source_job_id);
    };

    const handleBack = () => {
        setSelectedSource(null);
        setClips([]);
        setClipsError('');
    };

    const handleDeleteClip = (shortId: string) => {
        setClips(prev => prev.filter(c => c.short_id !== shortId));
        if (selectedSource) {
            setSources(prev =>
                prev.map(s =>
                    s.source_job_id === selectedSource.source_job_id
                        ? { ...s, shorts_count: Math.max(0, s.shorts_count - 1) }
                        : s
                )
            );
        }
    };

    const sidebar = (
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
                <Link
                    href="/audio-dub"
                    className="flex items-center gap-3 px-4 py-3 font-mono-label text-[#1A1A1A] hover:bg-[#eee7df] hover:translate-x-1 transition-all"
                >
                    <Music className="w-5 h-5" />
                    Audio Dub
                </Link>
                <div
                    className="flex items-center gap-3 px-4 py-3 font-mono-label text-white neo-border"
                    style={{ backgroundColor: '#9c48ea', boxShadow: '4px 4px 0px 0px #1A1A1A' }}
                >
                    <Scissors className="w-5 h-5" />
                    Shorts
                </div>
            </nav>
            <div className="mt-auto pt-4" style={{ borderTop: '3px solid #1A1A1A' }}>
                <UserButton afterSignOutUrl="/" />
            </div>
        </aside>
    );

    return (
        <div className="min-h-screen flex" style={{ backgroundColor: '#f4ede5' }}>
            {sidebar}

            <main className="flex-1 p-6 lg:p-10">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: -16 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8 flex items-center gap-4"
                >
                    {selectedSource && (
                        <motion.button
                            onClick={handleBack}
                            whileHover={{ x: -2 }}
                            className="p-2 neo-border bg-white text-[#1A1A1A] hover:bg-[#eee7df] transition-colors"
                            style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                        >
                            <ChevronLeft className="w-5 h-5" />
                        </motion.button>
                    )}
                    <div className="flex items-center gap-3">
                        <div className="p-2 neo-border" style={{ backgroundColor: '#9c48ea' }}>
                            <Scissors className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold font-headline text-[#1A1A1A]">
                                {selectedSource
                                    ? (selectedSource.input_file || '').split('/').pop() || 'Clips'
                                    : 'Shorts'}
                            </h2>
                            {!selectedSource && (
                                <p className="font-mono-label text-[#5c403d] text-sm">
                                    Clip highlights from your localized videos
                                </p>
                            )}
                            {selectedSource && (
                                <p className="font-mono-label text-[#5c403d] text-sm">
                                    {clips.length} clip{clips.length !== 1 ? 's' : ''} extracted
                                </p>
                            )}
                        </div>
                    </div>
                    {selectedSource && (
                        <motion.button
                            onClick={() => fetchClips(selectedSource.source_job_id)}
                            whileHover={{ rotate: 180 }}
                            className="ml-auto p-2 neo-border bg-white text-[#1A1A1A] hover:bg-[#eee7df] transition-colors"
                            style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                            title="Refresh clips"
                        >
                            <RefreshCw className={`w-4 h-4 ${loadingClips ? 'animate-spin' : ''}`} />
                        </motion.button>
                    )}
                </motion.div>

                {/* Source list view */}
                {!selectedSource && (
                    <div>
                        {loadingSources && (
                            <div className="flex items-center gap-3 py-12 justify-center">
                                <Loader2 className="w-5 h-5 animate-spin text-[#8127cf]" />
                                <span className="font-mono-label text-[#5c403d]">Loading sources...</span>
                            </div>
                        )}
                        {sourcesError && (
                            <div className="flex items-center gap-3 p-4 neo-border text-white mb-4"
                                style={{ backgroundColor: '#FF2D78' }}>
                                <AlertCircle className="w-4 h-4" />
                                <span className="font-mono-label text-sm">{sourcesError}</span>
                            </div>
                        )}
                        {!loadingSources && !sourcesError && sources.length === 0 && (
                            <div className="text-center py-20">
                                <div
                                    className="w-16 h-16 mx-auto mb-4 neo-border neo-shadow flex items-center justify-center"
                                    style={{ backgroundColor: '#F3EDFF' }}
                                >
                                    <Scissors className="w-8 h-8 text-[#8127cf]" />
                                </div>
                                <h3 className="text-lg font-bold text-[#1A1A1A] mb-2 font-headline">
                                    No shorts yet
                                </h3>
                                <p className="text-[#5c403d] font-mono-label text-sm mb-6">
                                    Open a completed video on the Dashboard and click the
                                    <br />scissors icon to generate shorts.
                                </p>
                                <Link href="/dashboard">
                                    <motion.div
                                        whileHover={{ y: -2, x: -2 }}
                                        whileTap={{ y: 2, x: 2 }}
                                        className="inline-flex items-center gap-2 px-5 py-2.5 text-white font-bold font-mono-label neo-border uppercase tracking-wider cursor-pointer"
                                        style={{ backgroundColor: '#ba061b', boxShadow: '4px 4px 0px 0px #1A1A1A' }}
                                    >
                                        <LayoutDashboard className="w-4 h-4" />
                                        Go to Dashboard
                                    </motion.div>
                                </Link>
                            </div>
                        )}
                        {!loadingSources && sources.length > 0 && (
                            <div className="space-y-3">
                                {sources.map(source => (
                                    <SourceCard
                                        key={source.source_job_id}
                                        source={source}
                                        onSelect={() => handleSelectSource(source)}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Clip list view */}
                {selectedSource && (
                    <div>
                        {loadingClips && (
                            <div className="flex items-center gap-3 py-12 justify-center">
                                <Loader2 className="w-5 h-5 animate-spin text-[#8127cf]" />
                                <span className="font-mono-label text-[#5c403d]">Loading clips...</span>
                            </div>
                        )}
                        {clipsError && (
                            <div className="flex items-center gap-3 p-4 neo-border text-white mb-4"
                                style={{ backgroundColor: '#FF2D78' }}>
                                <AlertCircle className="w-4 h-4" />
                                <span className="font-mono-label text-sm">{clipsError}</span>
                            </div>
                        )}
                        {!loadingClips && !clipsError && clips.length === 0 && (
                            <div className="text-center py-12">
                                <p className="font-mono-label text-[#5c403d]">
                                    No clips yet — generation may still be running.
                                </p>
                                <motion.button
                                    onClick={() => fetchClips(selectedSource.source_job_id)}
                                    whileHover={{ y: -2 }}
                                    className="mt-4 px-4 py-2 font-mono-label neo-border bg-white hover:bg-[#eee7df] transition-all text-[#1A1A1A] text-sm"
                                    style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                                >
                                    Refresh
                                </motion.button>
                            </div>
                        )}
                        {!loadingClips && clips.length > 0 && (
                            <div className="space-y-3">
                                {clips.map(clip => (
                                    <ClipCard
                                        key={clip.short_id}
                                        clip={clip}
                                        onDelete={handleDeleteClip}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}
