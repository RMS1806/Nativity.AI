'use client';

import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
    Download,
    Youtube,
    CheckCircle,
    XCircle,
    Loader2,
    Video,
    RefreshCw,
    Sparkles,
    X,
    Copy,
    Check,
    Eye,
    Play,
    FileText,
    Trash2,
    PartyPopper
} from 'lucide-react';
import { useHistory, HistoryVideo, useAuthenticatedApi } from '@/lib/auth-api';
import { CulturalInsight, CulturalReportModal } from './CulturalReport';
import VideoPreviewModal from './VideoPreviewModal';
import { downloadSrt, Segment } from '@/lib/srt-utils';

// ─── Modal active-state types ──────────────────────────────────────────
interface ActiveVideoModal {
    output_url: string;
    input_url?: string;
    fileName: string;
}
interface ActiveYoutubeModal {
    job_id: string;
}
interface ActiveInsightsModal {
    insights: CulturalInsight[];
    language: string;
}
interface ActiveDeleteModal {
    job_id: string;
    fileName: string;
}

// ─── Language display names ────────────────────────────────────────────
const LANGUAGE_NAMES: Record<string, { name: string; native: string }> = {
    hindi: { name: 'Hindi', native: 'हिंदी' },
    tamil: { name: 'Tamil', native: 'தமிழ்' },
    bengali: { name: 'Bengali', native: 'বাংলা' },
    telugu: { name: 'Telugu', native: 'తెలుగు' },
    marathi: { name: 'Marathi', native: 'मराठी' },
};

// ─── Confetti — neon palette ───────────────────────────────────────────
function fireConfetti() {
    const count = 200;
    const defaults = { origin: { y: 0.7 }, zIndex: 9999 };
    const fire = (ratio: number, opts: confetti.Options) =>
        confetti({ ...defaults, ...opts, particleCount: Math.floor(count * ratio) });
    fire(0.25, { spread: 26, startVelocity: 55, colors: ['#00E5FF', '#FF00FF', '#CCFF00'] });
    fire(0.20, { spread: 60, colors: ['#00E5FF', '#9000FF', '#FF00FF'] });
    fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8, colors: ['#FF00FF', '#00E5FF', '#CCFF00'] });
    fire(0.10, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2, colors: ['#00E5FF', '#CCFF00'] });
    fire(0.10, { spread: 120, startVelocity: 45, colors: ['#FF00FF', '#00E5FF'] });
}

function formatRelativeTime(isoString: string): string {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
}

// ─── Status Badge ──────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
    if (status === 'complete') {
        return (
            <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
                style={{ background: 'rgba(204,255,0,0.1)', border: '1px solid rgba(204,255,0,0.35)', color: '#CCFF00' }}
            >
                <CheckCircle className="w-3.5 h-3.5" /> Complete
            </span>
        );
    }
    if (status === 'failed') {
        return (
            <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
                style={{ background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.3)', color: '#ff6060' }}
            >
                <XCircle className="w-3.5 h-3.5" /> Failed
            </span>
        );
    }
    return (
        <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold"
            style={{ background: 'rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.35)', color: '#00E5FF' }}
        >
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Processing
        </span>
    );
}

// ─── Copy Button ───────────────────────────────────────────────────────
function CopyButton({ text, label }: { text: string; label: string }) {
    const [copied, setCopied] = useState(false);
    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch { }
    };
    return (
        <motion.button
            onClick={handleCopy}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors"
            style={
                copied
                    ? { background: 'rgba(204,255,0,0.1)', border: '1px solid rgba(204,255,0,0.35)', color: '#CCFF00' }
                    : { background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: '#9ca3af' }
            }
        >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : label}
        </motion.button>
    );
}

// ─── YouTube Modal ─────────────────────────────────────────────────────
// Rendered at root level — receives job_id and close callback
function YouTubeMetadataModal({
    isOpen,
    onClose,
    jobId,
}: {
    isOpen: boolean;
    onClose: () => void;
    jobId: string;
}) {
    const [metadata, setMetadata] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const api = useAuthenticatedApi();

    const fetchMetadata = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await api.post('/api/video/metadata', { job_id: jobId });
            setMetadata(response.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to generate metadata');
        } finally {
            setLoading(false);
        }
    };

    // Fetch when opening; reset when closing
    useEffect(() => {
        if (isOpen && jobId) { setMetadata(null); fetchMetadata(); }
        if (!isOpen) { setMetadata(null); setError(null); }
    }, [isOpen, jobId]); // eslint-disable-line react-hooks/exhaustive-deps

    if (!isOpen) return null;

    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(16px)' }}
            onClick={onClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="max-w-2xl w-full max-h-[80vh] overflow-hidden rounded-2xl"
                style={{ background: 'rgba(10,10,20,0.97)', border: '1px solid rgba(255,255,255,0.1)' }}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ background: 'rgba(255,0,0,0.12)', border: '1px solid rgba(255,0,0,0.3)' }}>
                            <Youtube className="w-5 h-5 text-red-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">YouTube Export</h2>
                            <p className="text-sm text-gray-500">AI-generated SEO metadata</p>
                        </div>
                    </div>
                    <motion.button
                        onClick={onClose}
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                        className="p-2 text-gray-500 hover:text-white rounded-lg transition-colors"
                        style={{ background: 'rgba(255,255,255,0.05)' }}
                    >
                        <X className="w-5 h-5" />
                    </motion.button>
                </div>

                <div className="p-5 overflow-y-auto max-h-[60vh]">
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <div className="border-spin-wrapper w-14 h-14 rounded-full mb-4">
                                <div className="border-spin-inner w-full h-full rounded-full flex items-center justify-center">
                                    <Youtube className="w-6 h-6 text-red-400" />
                                </div>
                            </div>
                            <p className="text-gray-400">Generating SEO metadata…</p>
                        </div>
                    )}
                    {error && (
                        <div className="rounded-lg p-4 text-center"
                            style={{ background: 'rgba(255,60,60,0.05)', border: '1px solid rgba(255,60,60,0.25)' }}>
                            <p className="text-red-400">{error}</p>
                            <motion.button
                                onClick={fetchMetadata}
                                whileHover={{ scale: 1.05 }}
                                className="mt-3 px-4 py-2 rounded-lg text-sm text-red-400"
                                style={{ background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.3)' }}
                            >
                                Try Again
                            </motion.button>
                        </div>
                    )}
                    {metadata && !loading && (
                        <div className="space-y-4">
                            {[
                                { key: 'title', label: 'Title', content: metadata.title },
                                { key: 'description', label: 'Description', content: metadata.description },
                            ].map(({ key, label, content }) => (
                                <div key={key} className="rounded-xl p-4"
                                    style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                                    <div className="flex items-center justify-between mb-2">
                                        <label className="text-sm font-medium text-gray-500">{label}</label>
                                        <CopyButton text={content} label="Copy" />
                                    </div>
                                    <p className="text-white text-sm whitespace-pre-wrap">{content}</p>
                                </div>
                            ))}
                            <div className="rounded-xl p-4"
                                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
                                <div className="flex items-center justify-between mb-3">
                                    <label className="text-sm font-medium text-gray-500">Tags</label>
                                    <CopyButton text={metadata.tags?.join(', ') || ''} label="Copy All" />
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {metadata.tags?.map((tag: string, i: number) => (
                                        <span key={i} className="px-2 py-1 rounded text-xs"
                                            style={{ background: 'rgba(0,229,255,0.08)', border: '1px solid rgba(0,229,255,0.2)', color: '#00E5FF' }}>
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
}

// ─── Delete Confirm Modal ──────────────────────────────────────────────
function DeleteConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    fileName,
    isDeleting,
}: {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    fileName: string;
    isDeleting: boolean;
}) {
    if (!isOpen) return null;
    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.88)', backdropFilter: 'blur(16px)' }}
            onClick={onClose}
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.85 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="max-w-md w-full rounded-2xl"
                style={{ background: 'rgba(10,10,20,0.98)', border: '1px solid rgba(255,60,60,0.2)' }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6 text-center">
                    <div className="w-14 h-14 mx-auto mb-4 rounded-full flex items-center justify-center"
                        style={{ background: 'rgba(255,60,60,0.08)', border: '1px solid rgba(255,60,60,0.3)' }}>
                        <Trash2 className="w-7 h-7 text-red-400" />
                    </div>
                    <h3 className="text-xl font-bold text-white mb-2">Delete Video?</h3>
                    <p className="text-gray-400 text-sm mb-6">
                        Delete <span className="text-white font-medium">{fileName}</span>?
                    </p>
                    <div className="flex gap-3">
                        <motion.button
                            onClick={onClose}
                            disabled={isDeleting}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 px-4 py-2.5 rounded-xl text-gray-300 transition-colors"
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
                        >
                            Cancel
                        </motion.button>
                        <motion.button
                            onClick={onConfirm}
                            disabled={isDeleting}
                            whileHover={{ scale: 1.02, boxShadow: '0 0 20px rgba(255,60,60,0.4)' }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
                        >
                            {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                            {isDeleting ? 'Deleting…' : 'Delete'}
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}

// ─── Action Button ─────────────────────────────────────────────────────
function ActionButton({ onClick, icon: Icon, title, variant = 'default', disabled = false, href }: {
    onClick?: () => void;
    icon: any;
    title: string;
    variant?: 'default' | 'danger';
    disabled?: boolean;
    href?: string;
}) {
    const style = variant === 'danger' ? { color: '#64748b' } : { color: '#64748b' };

    const content = (
        <motion.button
            onClick={onClick}
            disabled={disabled}
            whileHover={{ scale: 1.15, color: variant === 'danger' ? '#ff6060' : '#00E5FF' }}
            whileTap={{ scale: 0.9 }}
            className="p-2 rounded-lg transition-colors disabled:opacity-50"
            style={style}
            title={title}
        >
            <Icon className={`w-5 h-5 ${disabled && Icon === Loader2 ? 'animate-spin' : ''}`} />
        </motion.button>
    );

    if (href) {
        return (
            <motion.a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                whileHover={{ scale: 1.15, color: '#00E5FF' }}
                whileTap={{ scale: 0.9 }}
                className="p-2 rounded-lg transition-colors"
                style={style}
                title={title}
            >
                <Icon className="w-5 h-5" />
            </motion.a>
        );
    }
    return content;
}

// ─── Video Row (Card) ──────────────────────────────────────────────────
// No modal state or modal rendering here — this component only fires callbacks.
interface VideoRowCallbacks {
    onOpenVideo: (v: ActiveVideoModal) => void;
    onOpenYoutube: (v: ActiveYoutubeModal) => void;
    onOpenInsights: (v: ActiveInsightsModal) => void;
    onOpenDelete: (v: ActiveDeleteModal) => void;
}

function VideoRow({
    video,
    onFirstDownload,
    onOpenVideo,
    onOpenYoutube,
    onOpenInsights,
    onOpenDelete,
}: {
    video: HistoryVideo;
    onFirstDownload: (jobId: string) => void;
} & VideoRowCallbacks) {
    const [segments, setSegments] = useState<Segment[]>([]);
    const [loadingSrt, setLoadingSrt] = useState(false);
    const [fetchingInsights, setFetchingInsights] = useState(false);
    const api = useAuthenticatedApi();

    const language = LANGUAGE_NAMES[video.target_language] || { name: video.target_language, native: '' };
    const fileName = video.input_file.split('/').pop() || 'Video';

    const handleShowInsights = async () => {
        setFetchingInsights(true);
        try {
            const response = await api.get(`/api/video/job/${video.job_id}/analysis`);
            const insights = response.data?.cultural_analysis ?? [];
            const segs = response.data?.segments ?? [];
            if (segs.length > 0) setSegments(segs);
            onOpenInsights({ insights, language: language.name });
        } catch {
            // Still open modal even with empty insights
            onOpenInsights({ insights: [], language: language.name });
        } finally {
            setFetchingInsights(false);
        }
    };

    const handleDownloadSrt = async () => {
        if (segments.length > 0) { downloadSrt(segments, fileName); return; }
        setLoadingSrt(true);
        try {
            const response = await api.get(`/api/video/job/${video.job_id}/analysis`);
            if (response.data?.segments?.length > 0) {
                setSegments(response.data.segments);
                downloadSrt(response.data.segments, fileName);
            }
        } catch { } finally { setLoadingSrt(false); }
    };

    const handleDownloadClick = () => {
        onFirstDownload(video.job_id);
        if (video.output_url) window.open(video.output_url, '_blank');
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            whileHover={{ scale: 1.015, y: -2 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="flex items-center gap-4 p-4 rounded-xl transition-all"
            style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.07)',
                marginBottom: '8px',
            }}
        >
            {/* Thumbnail */}
            <motion.div
                whileHover={{ scale: 1.05 }}
                className="relative w-20 h-14 rounded-xl flex items-center justify-center flex-shrink-0 cursor-pointer group overflow-hidden"
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
                onClick={() =>
                    video.status === 'complete' && video.output_url &&
                    onOpenVideo({ output_url: video.output_url, input_url: video.input_url, fileName })
                }
            >
                <Video className="w-5 h-5 text-gray-600 group-hover:hidden" />
                {video.status === 'complete' && video.output_url && (
                    <Play className="w-5 h-5 hidden group-hover:block" style={{ color: '#FF00FF' }} />
                )}
            </motion.div>

            {/* Info */}
            <div className="flex-grow min-w-0">
                <h3 className="font-medium text-white truncate">{fileName}</h3>
                <div className="flex items-center gap-2 mt-1 text-sm text-gray-500">
                    <span className="text-gray-400">{language.name}</span>
                    <span className="text-gray-700">•</span>
                    <span>{formatRelativeTime(video.created_at)}</span>
                    {video.file_size_mb && (
                        <>
                            <span className="text-gray-700">•</span>
                            <span>{video.file_size_mb.toFixed(1)} MB</span>
                        </>
                    )}
                </div>
            </div>

            {/* Status */}
            <StatusBadge status={video.status} />

            {/* Actions */}
            <div className="flex items-center gap-1 flex-shrink-0">
                {video.status === 'complete' && video.output_url && (
                    <>
                        <ActionButton onClick={handleDownloadClick} icon={Download} title="Download" />
                        {video.subtitle_url ? (
                            <ActionButton href={video.subtitle_url} icon={FileText} title="Download Subtitles (VTT)" />
                        ) : (
                            <ActionButton
                                onClick={handleDownloadSrt}
                                icon={loadingSrt ? Loader2 : FileText}
                                title="Download SRT"
                                disabled={loadingSrt}
                            />
                        )}
                        <ActionButton
                            onClick={handleShowInsights}
                            icon={fetchingInsights ? Loader2 : Eye}
                            title="Cultural Insights"
                            disabled={fetchingInsights}
                        />
                        <ActionButton
                            onClick={() => onOpenYoutube({ job_id: video.job_id })}
                            icon={Youtube}
                            title="YouTube Export"
                        />
                    </>
                )}
                <ActionButton
                    onClick={() => onOpenDelete({ job_id: video.job_id, fileName })}
                    icon={Trash2}
                    title="Delete"
                    variant="danger"
                />
            </div>
        </motion.div>
    );
}

// ─── Empty State ────────────────────────────────────────────────────────
function EmptyState() {
    return (
        <div className="text-center py-16">
            <div
                className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(0,229,255,0.06)', border: '1px solid rgba(0,229,255,0.15)' }}
            >
                <Sparkles className="w-8 h-8" style={{ color: '#00E5FF' }} />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">No videos yet</h3>
            <p className="text-gray-500 mb-6">Create your first localized video!</p>
            <motion.a
                href="/"
                whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(0,229,255,0.3)' }}
                whileTap={{ scale: 0.95 }}
                className="inline-flex items-center gap-2 px-5 py-2.5 text-black font-bold rounded-xl"
                style={{ background: 'linear-gradient(135deg, #00E5FF, #FF00FF)' }}
            >
                <Sparkles className="w-4 h-4" />
                Create Video
            </motion.a>
        </div>
    );
}

// ─── Loading Skeleton ───────────────────────────────────────────────────
function LoadingSkeleton() {
    return (
        <div className="space-y-2">
            {[1, 2, 3].map((i) => (
                <div
                    key={i}
                    className="flex items-center gap-4 p-4 rounded-xl animate-pulse"
                    style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)' }}
                >
                    <div className="w-20 h-14 rounded-xl" style={{ background: 'rgba(255,255,255,0.06)' }} />
                    <div className="flex-grow space-y-2">
                        <div className="h-4 rounded w-1/3" style={{ background: 'rgba(255,255,255,0.07)' }} />
                        <div className="h-3 rounded w-1/2" style={{ background: 'rgba(255,255,255,0.04)' }} />
                    </div>
                    <div className="h-6 rounded-full w-20" style={{ background: 'rgba(255,255,255,0.06)' }} />
                </div>
            ))}
        </div>
    );
}

// ─── Main Export ────────────────────────────────────────────────────────
export default function HistoryTable() {
    const { data, loading, error, refetch } = useHistory();
    const [videos, setVideos] = useState<HistoryVideo[]>([]);
    const [downloadedJobs, setDownloadedJobs] = useState<Set<string>>(new Set());
    const prevStatusesRef = useRef<Map<string, string>>(new Map());

    // ── Modal states (all at root — outside every motion.div) ──────────
    const [activeVideoModal, setActiveVideoModal] = useState<ActiveVideoModal | null>(null);
    const [activeYoutubeModal, setActiveYoutubeModal] = useState<ActiveYoutubeModal | null>(null);
    const [activeInsightsModal, setActiveInsightsModal] = useState<ActiveInsightsModal | null>(null);
    const [activeDeleteModal, setActiveDeleteModal] = useState<ActiveDeleteModal | null>(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const api = useAuthenticatedApi();

    useEffect(() => {
        if (data?.videos) {
            const newVideos = data.videos;
            newVideos.forEach(video => {
                const prevStatus = prevStatusesRef.current.get(video.job_id);
                if (prevStatus && prevStatus !== 'complete' && video.status === 'complete') {
                    fireConfetti();
                }
                prevStatusesRef.current.set(video.job_id, video.status);
            });
            setVideos(newVideos);
        }
    }, [data?.videos]);

    const handleDeleteVideo = (jobId: string) =>
        setVideos(prev => prev.filter(v => v.job_id !== jobId));

    const handleFirstDownload = (jobId: string) => {
        if (!downloadedJobs.has(jobId)) {
            fireConfetti();
            setDownloadedJobs(prev => new Set([...prev, jobId]));
        }
    };

    // Delete lives here so it can mutate the video list after success
    const handleConfirmDelete = async () => {
        if (!activeDeleteModal) return;
        setIsDeleting(true);
        try {
            await api.delete(`/api/video/${activeDeleteModal.job_id}`);
            handleDeleteVideo(activeDeleteModal.job_id);
            setActiveDeleteModal(null);
        } catch { } finally { setIsDeleting(false); }
    };

    return (
        <div className="space-y-4">
            {/* Header */}
            <div
                className="flex items-center justify-between px-2 pb-4"
                style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
            >
                <h2 className="text-sm font-bold text-white uppercase tracking-widest flex items-center gap-2">
                    <PartyPopper className="w-4 h-4" style={{ color: '#00E5FF' }} />
                    Recent Projects
                    {videos.length > 0 && (
                        <span
                            className="ml-2 px-2 py-0.5 text-xs rounded-full"
                            style={{ background: 'rgba(0,229,255,0.1)', border: '1px solid rgba(0,229,255,0.25)', color: '#00E5FF' }}
                        >
                            {videos.length}
                        </span>
                    )}
                </h2>
                <motion.button
                    whileHover={{ scale: 1.1, rotate: 180, color: '#00E5FF' }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => refetch()}
                    disabled={loading}
                    className="p-2 text-gray-500 rounded-lg transition-colors disabled:opacity-50"
                    title="Refresh"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </motion.button>
            </div>

            {/* Content */}
            <div>
                {loading && !data && <LoadingSkeleton />}

                {error && (
                    <div
                        className="p-4 rounded-xl text-red-400 text-sm"
                        style={{ background: 'rgba(255,60,60,0.05)', border: '1px solid rgba(255,60,60,0.2)' }}
                    >
                        {error}
                    </div>
                )}

                {!loading && !error && videos.length === 0 && <EmptyState />}

                {videos.length > 0 && (
                    <div>
                        {videos.map(video => (
                            <VideoRow
                                key={video.job_id}
                                video={video}
                                onFirstDownload={handleFirstDownload}
                                onOpenVideo={setActiveVideoModal}
                                onOpenYoutube={setActiveYoutubeModal}
                                onOpenInsights={setActiveInsightsModal}
                                onOpenDelete={setActiveDeleteModal}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* ── Root-level Modals ──────────────────────────────────────
                Rendered OUTSIDE every motion.div / transform container.
                This prevents the CSS stacking context created by framer-motion
                whileHover transforms from clipping fixed-position overlays.
            ─────────────────────────────────────────────────────────── */}

            {activeVideoModal && (
                <VideoPreviewModal
                    isOpen
                    onClose={() => setActiveVideoModal(null)}
                    localizedVideoUrl={activeVideoModal.output_url}
                    originalVideoUrl={activeVideoModal.input_url}
                    fileName={activeVideoModal.fileName}
                />
            )}

            <YouTubeMetadataModal
                isOpen={!!activeYoutubeModal}
                onClose={() => setActiveYoutubeModal(null)}
                jobId={activeYoutubeModal?.job_id ?? ''}
            />

            <CulturalReportModal
                isOpen={!!activeInsightsModal}
                onClose={() => setActiveInsightsModal(null)}
                insights={activeInsightsModal?.insights ?? []}
                language={activeInsightsModal?.language}
            />

            <DeleteConfirmModal
                isOpen={!!activeDeleteModal}
                onClose={() => { if (!isDeleting) setActiveDeleteModal(null); }}
                onConfirm={handleConfirmDelete}
                fileName={activeDeleteModal?.fileName ?? ''}
                isDeleting={isDeleting}
            />
        </div>
    );
}
