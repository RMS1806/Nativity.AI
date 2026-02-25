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
import { CulturalReportModal, CulturalInsight } from './CulturalReport';
import VideoPreviewModal from './VideoPreviewModal';
import { downloadSrt, Segment } from '@/lib/srt-utils';

// Language display names
const LANGUAGE_NAMES: Record<string, { name: string; native: string }> = {
    hindi: { name: 'Hindi', native: 'हिंदी' },
    tamil: { name: 'Tamil', native: 'தமிழ்' },
    bengali: { name: 'Bengali', native: 'বাংলা' },
    telugu: { name: 'Telugu', native: 'తెలుగు' },
    marathi: { name: 'Marathi', native: 'मराठी' },
};

// Confetti celebration function
function fireConfetti() {
    const count = 200;
    const defaults = {
        origin: { y: 0.7 },
        zIndex: 9999,
    };

    function fire(particleRatio: number, opts: confetti.Options) {
        confetti({
            ...defaults,
            ...opts,
            particleCount: Math.floor(count * particleRatio),
        });
    }

    // Fire multiple bursts for epic effect
    fire(0.25, { spread: 26, startVelocity: 55, colors: ['#a855f7', '#d946ef', '#ec4899'] });
    fire(0.2, { spread: 60, colors: ['#a855f7', '#8b5cf6', '#7c3aed'] });
    fire(0.35, { spread: 100, decay: 0.91, scalar: 0.8, colors: ['#c026d3', '#a855f7', '#9333ea'] });
    fire(0.1, { spread: 120, startVelocity: 25, decay: 0.92, scalar: 1.2, colors: ['#f0abfc', '#e879f9', '#d946ef'] });
    fire(0.1, { spread: 120, startVelocity: 45, colors: ['#a855f7', '#8b5cf6', '#7c3aed'] });
}

// Format relative time
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

// Status Badge - Dark Tech Style
function StatusBadge({ status }: { status: string }) {
    if (status === 'complete') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-900/50 text-green-400 border border-green-800">
                <CheckCircle className="w-3.5 h-3.5" />
                Complete
            </span>
        );
    }

    if (status === 'failed') {
        return (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-900/50 text-red-400 border border-red-800">
                <XCircle className="w-3.5 h-3.5" />
                Failed
            </span>
        );
    }

    return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-900/50 text-blue-400 border border-blue-800 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Processing
        </span>
    );
}

// Copy Button
function CopyButton({ text, label }: { text: string; label: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    return (
        <motion.button
            onClick={handleCopy}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${copied
                ? 'bg-green-900/50 text-green-400 border border-green-800'
                : 'bg-gray-800 text-gray-400 hover:text-white border border-gray-700'
                }`}
        >
            {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied!' : label}
        </motion.button>
    );
}

// YouTube Modal - Dark Tech
function YouTubeMetadataModal({ isOpen, onClose, jobId }: { isOpen: boolean; onClose: () => void; jobId: string; }) {
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

    if (isOpen && !metadata && !loading && !error) fetchMetadata();
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4" onClick={onClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between p-5 border-b border-gray-800">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-red-900/50 border border-red-800 flex items-center justify-center">
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
                        className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </motion.button>
                </div>

                <div className="p-5 overflow-y-auto max-h-[60vh]">
                    {loading && (
                        <div className="flex flex-col items-center justify-center py-12">
                            <Loader2 className="w-10 h-10 text-fuchsia-500 animate-spin mb-4" />
                            <p className="text-gray-400">Generating SEO metadata...</p>
                        </div>
                    )}

                    {error && (
                        <div className="bg-red-900/30 border border-red-800 rounded-lg p-4 text-center">
                            <p className="text-red-400">{error}</p>
                            <motion.button
                                onClick={fetchMetadata}
                                whileHover={{ scale: 1.05 }}
                                className="mt-3 px-4 py-2 bg-red-900/50 text-red-400 rounded-lg hover:bg-red-900/70 text-sm border border-red-800"
                            >
                                Try Again
                            </motion.button>
                        </div>
                    )}

                    {metadata && !loading && (
                        <div className="space-y-5">
                            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <label className="text-sm font-medium text-gray-500">Title</label>
                                    <CopyButton text={metadata.title} label="Copy" />
                                </div>
                                <p className="text-white font-medium">{metadata.title}</p>
                            </div>

                            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <label className="text-sm font-medium text-gray-500">Description</label>
                                    <CopyButton text={metadata.description} label="Copy" />
                                </div>
                                <p className="text-gray-300 whitespace-pre-wrap text-sm">{metadata.description}</p>
                            </div>

                            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <label className="text-sm font-medium text-gray-500">Tags</label>
                                    <CopyButton text={metadata.tags?.join(', ') || ''} label="Copy All" />
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    {metadata.tags?.map((tag: string, index: number) => (
                                        <span key={index} className="px-2 py-1 bg-fuchsia-900/30 text-fuchsia-400 border border-fuchsia-800 rounded text-xs">
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

// Delete Confirmation Modal - Dark Tech
function DeleteConfirmModal({ isOpen, onClose, onConfirm, fileName, isDeleting }: { isOpen: boolean; onClose: () => void; onConfirm: () => void; fileName: string; isDeleting: boolean; }) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4" onClick={onClose}>
            <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl max-w-md w-full"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6 text-center">
                    <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-900/30 border border-red-800 flex items-center justify-center">
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
                            className="flex-1 px-4 py-2.5 bg-gray-800 text-gray-300 rounded-lg border border-gray-700 hover:bg-gray-700 transition-colors"
                        >
                            Cancel
                        </motion.button>
                        <motion.button
                            onClick={onConfirm}
                            disabled={isDeleting}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 px-4 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                            {isDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                            {isDeleting ? 'Deleting...' : 'Delete'}
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}

// Action Button with Animation
function ActionButton({ onClick, icon: Icon, title, variant = 'default', disabled = false, href }: { onClick?: () => void; icon: any; title: string; variant?: 'default' | 'danger'; disabled?: boolean; href?: string; }) {
    const baseClass = "p-2 rounded-lg transition-colors";
    const variantClass = variant === 'danger'
        ? "text-gray-500 hover:text-red-400 hover:bg-red-900/20"
        : "text-gray-500 hover:text-white hover:bg-gray-800";

    const content = (
        <motion.button
            onClick={onClick}
            disabled={disabled}
            whileHover={{ scale: 1.15 }}
            whileTap={{ scale: 0.9 }}
            className={`${baseClass} ${variantClass} disabled:opacity-50`}
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
                whileHover={{ scale: 1.15 }}
                whileTap={{ scale: 0.9 }}
                className={`${baseClass} ${variantClass}`}
                title={title}
            >
                <Icon className="w-5 h-5" />
            </motion.a>
        );
    }

    return content;
}

// Video Row - Dark Tech Style with Confetti
function VideoRow({ video, onDelete, onFirstDownload }: { video: HistoryVideo; onDelete: (jobId: string) => void; onFirstDownload: (jobId: string) => void; }) {
    const [showYouTubeModal, setShowYouTubeModal] = useState(false);
    const [showInsightsModal, setShowInsightsModal] = useState(false);
    const [showVideoPreview, setShowVideoPreview] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [culturalInsights, setCulturalInsights] = useState<CulturalInsight[]>([]);
    const [segments, setSegments] = useState<Segment[]>([]);
    const [loadingSrt, setLoadingSrt] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const api = useAuthenticatedApi();

    const language = LANGUAGE_NAMES[video.target_language] || { name: video.target_language, native: '' };
    const fileName = video.input_file.split('/').pop() || 'Video';

    const handleShowInsights = async () => {
        setShowInsightsModal(true);
        if (culturalInsights.length === 0) {
            try {
                const response = await api.get(`/api/video/job/${video.job_id}/analysis`);
                if (response.data?.cultural_analysis) setCulturalInsights(response.data.cultural_analysis);
                if (response.data?.segments) setSegments(response.data.segments);
            } catch (err) {
                console.error('Failed to fetch cultural insights:', err);
            }
        }
    };

    const handleDownloadSrt = async () => {
        if (segments.length > 0) {
            downloadSrt(segments, fileName);
            return;
        }
        setLoadingSrt(true);
        try {
            const response = await api.get(`/api/video/job/${video.job_id}/analysis`);
            if (response.data?.segments?.length > 0) {
                setSegments(response.data.segments);
                downloadSrt(response.data.segments, fileName);
            }
        } catch (err) {
            console.error('Failed to fetch segments for SRT:', err);
        } finally {
            setLoadingSrt(false);
        }
    };

    const handleDelete = async () => {
        setIsDeleting(true);
        try {
            await api.delete(`/api/video/${video.job_id}`);
            setShowDeleteModal(false);
            onDelete(video.job_id);
        } catch (err) {
            console.error('Failed to delete video:', err);
        } finally {
            setIsDeleting(false);
        }
    };

    const handleDownloadClick = () => {
        onFirstDownload(video.job_id);
        // Open download in new tab
        if (video.output_url) {
            window.open(video.output_url, '_blank');
        }
    };

    return (
        <>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                whileHover={{ backgroundColor: 'rgba(31, 41, 55, 0.5)' }}
                className="flex items-center gap-4 p-4 bg-gray-900/50 border-b border-gray-800 transition-colors"
            >
                {/* Thumbnail */}
                <motion.div
                    whileHover={{ scale: 1.05 }}
                    className="relative w-20 h-14 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-center flex-shrink-0 cursor-pointer group"
                    onClick={() => video.status === 'complete' && video.output_url && setShowVideoPreview(true)}
                >
                    <Video className="w-5 h-5 text-gray-600 group-hover:hidden" />
                    {video.status === 'complete' && video.output_url && (
                        <Play className="w-5 h-5 text-fuchsia-500 hidden group-hover:block" />
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
                            {/* Subtitle download: use server-generated VTT if available, else fall back to SRT */}
                            {video.subtitle_url ? (
                                <ActionButton
                                    href={video.subtitle_url}
                                    icon={FileText}
                                    title="Download Subtitles (VTT)"
                                />
                            ) : (
                                <ActionButton
                                    onClick={handleDownloadSrt}
                                    icon={loadingSrt ? Loader2 : FileText}
                                    title="Download SRT"
                                    disabled={loadingSrt}
                                />
                            )}
                            <ActionButton onClick={handleShowInsights} icon={Eye} title="Cultural Insights" />
                            <ActionButton onClick={() => setShowYouTubeModal(true)} icon={Youtube} title="YouTube Export" />
                        </>
                    )}
                    <ActionButton onClick={() => setShowDeleteModal(true)} icon={Trash2} title="Delete" variant="danger" />
                </div>
            </motion.div>

            {/* Modals */}
            <YouTubeMetadataModal isOpen={showYouTubeModal} onClose={() => setShowYouTubeModal(false)} jobId={video.job_id} />
            <CulturalReportModal isOpen={showInsightsModal} onClose={() => setShowInsightsModal(false)} insights={culturalInsights} language={language.name} />
            {video.output_url && (
                <VideoPreviewModal
                    isOpen={showVideoPreview}
                    onClose={() => setShowVideoPreview(false)}
                    localizedVideoUrl={video.output_url}
                    originalVideoUrl={video.input_url}
                    fileName={fileName}
                />
            )}
            <DeleteConfirmModal isOpen={showDeleteModal} onClose={() => setShowDeleteModal(false)} onConfirm={handleDelete} fileName={fileName} isDeleting={isDeleting} />
        </>
    );
}

// Empty state
function EmptyState() {
    return (
        <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-gray-600" />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">No videos yet</h3>
            <p className="text-gray-500 mb-6">Create your first localized video!</p>
            <motion.a
                href="/"
                whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(168, 85, 247, 0.3)' }}
                whileTap={{ scale: 0.95 }}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-fuchsia-600 to-purple-600 text-white font-bold rounded-lg"
            >
                <Sparkles className="w-4 h-4" />
                Create Video
            </motion.a>
        </div>
    );
}

// Loading skeleton
function LoadingSkeleton() {
    return (
        <div className="divide-y divide-gray-800">
            {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-gray-900/50 animate-pulse">
                    <div className="w-20 h-14 rounded-lg bg-gray-800" />
                    <div className="flex-grow space-y-2">
                        <div className="h-4 bg-gray-800 rounded w-1/3" />
                        <div className="h-3 bg-gray-800/50 rounded w-1/2" />
                    </div>
                    <div className="h-6 bg-gray-800 rounded-full w-20" />
                </div>
            ))}
        </div>
    );
}

export default function HistoryTable() {
    const { data, loading, error, refetch } = useHistory();
    const [videos, setVideos] = useState<HistoryVideo[]>([]);
    const [downloadedJobs, setDownloadedJobs] = useState<Set<string>>(new Set());
    const prevStatusesRef = useRef<Map<string, string>>(new Map());

    // Update videos and check for status changes (for confetti)
    useEffect(() => {
        if (data?.videos) {
            const newVideos = data.videos;

            // Check for newly completed videos
            newVideos.forEach(video => {
                const prevStatus = prevStatusesRef.current.get(video.job_id);
                if (prevStatus && prevStatus !== 'complete' && video.status === 'complete') {
                    // Video just completed! 🎉
                    fireConfetti();
                }
                prevStatusesRef.current.set(video.job_id, video.status);
            });

            setVideos(newVideos);
        }
    }, [data?.videos]);

    const handleDelete = (jobId: string) => {
        setVideos(prev => prev.filter(v => v.job_id !== jobId));
    };

    const handleFirstDownload = (jobId: string) => {
        if (!downloadedJobs.has(jobId)) {
            // First download - celebrate!
            fireConfetti();
            setDownloadedJobs(prev => new Set([...prev, jobId]));
        }
    };

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700 rounded-t-lg -mx-6 -mt-6">
                <h2 className="text-sm font-bold text-white uppercase tracking-wide flex items-center gap-2">
                    <PartyPopper className="w-4 h-4 text-fuchsia-500" />
                    Recent Projects
                    {videos.length > 0 && (
                        <span className="ml-2 px-2 py-0.5 text-xs bg-fuchsia-900/30 text-fuchsia-400 border border-fuchsia-800 rounded-full">
                            {videos.length}
                        </span>
                    )}
                </h2>
                <motion.button
                    whileHover={{ scale: 1.1, rotate: 180 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => refetch()}
                    disabled={loading}
                    className="p-2 text-gray-500 hover:text-white rounded-lg transition-colors disabled:opacity-50"
                    title="Refresh"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </motion.button>
            </div>

            {/* Content */}
            <div className="-mx-6 -mb-6 overflow-hidden rounded-b-lg">
                {loading && !data && <LoadingSkeleton />}

                {error && (
                    <div className="p-4 m-4 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
                        {error}
                    </div>
                )}

                {!loading && !error && videos.length === 0 && <EmptyState />}

                {videos.length > 0 && (
                    <div className="divide-y divide-gray-800">
                        {videos.map((video) => (
                            <VideoRow
                                key={video.job_id}
                                video={video}
                                onDelete={handleDelete}
                                onFirstDownload={handleFirstDownload}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
