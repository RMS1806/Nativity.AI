'use client';

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    Save,
    Sparkles,
    Clock,
    Languages,
    ChevronLeft,
    ChevronRight,
    Loader2,
    CheckCircle,
    AlertCircle,
    Wand2
} from 'lucide-react';
import { useAuthenticatedApi } from '@/lib/auth-api';

interface Segment {
    index: number;
    start: number;
    end: number;
    original_text: string;
    translated_text: string;
    cultural_notes?: string;
    is_approved?: boolean;
}

interface SubtitleEditorProps {
    isOpen: boolean;
    onClose: () => void;
    jobId: string;
    segments: Segment[];
    language: string;
    onFinalize: () => void;
}

// Format time as MM:SS.ms
function formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
}

export default function SubtitleEditor({
    isOpen,
    onClose,
    jobId,
    segments: initialSegments,
    language,
    onFinalize
}: SubtitleEditorProps) {
    const [segments, setSegments] = useState<Segment[]>(initialSegments);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [saveSuccess, setSaveSuccess] = useState(false);
    const api = useAuthenticatedApi();

    // Update segment text
    const updateSegment = useCallback((index: number, field: 'translated_text' | 'is_approved', value: string | boolean) => {
        setSegments(prev => prev.map((seg, i) =>
            i === index ? { ...seg, [field]: value } : seg
        ));
    }, []);

    // Navigate between segments
    const goToSegment = (index: number) => {
        if (index >= 0 && index < segments.length) {
            setCurrentIndex(index);
        }
    };

    // Save and finalize
    const handleFinalize = async () => {
        setIsSaving(true);
        setError(null);

        try {
            // Mark all segments as approved
            const approvedSegments = segments.map(seg => ({
                ...seg,
                is_approved: true
            }));

            await api.post('/api/video/finalize', {
                job_id: jobId,
                approved_segments: approvedSegments
            });

            setSaveSuccess(true);
            setTimeout(() => {
                onFinalize();
                onClose();
            }, 1500);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to start dubbing');
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    const currentSegment = segments[currentIndex];
    const progress = ((currentIndex + 1) / segments.length) * 100;

    return (
        <AnimatePresence>
            {/* Synthesizing Voice Overlay */}
            {isSaving && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="fixed inset-0 bg-black/95 backdrop-blur-lg z-[60] flex flex-col items-center justify-center"
                >
                    <motion.div
                        initial={{ scale: 0.8, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: 'spring', damping: 15 }}
                        className="text-center"
                    >
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                            className="w-20 h-20 mx-auto mb-6 rounded-full border-4 border-fuchsia-500/30 border-t-fuchsia-500"
                        />
                        <h2 className="text-2xl font-bold text-white mb-2">
                            Synthesizing Voice...
                        </h2>
                        <p className="text-gray-400 max-w-md">
                            Generating natural speech for {segments.length} segments. This may take a minute.
                        </p>
                        <div className="mt-6 flex items-center justify-center gap-2">
                            <motion.span
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                                className="w-2 h-2 bg-fuchsia-500 rounded-full"
                            />
                            <motion.span
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                                className="w-2 h-2 bg-purple-500 rounded-full"
                            />
                            <motion.span
                                animate={{ opacity: [0.3, 1, 0.3] }}
                                transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
                                className="w-2 h-2 bg-violet-500 rounded-full"
                            />
                        </div>
                    </motion.div>
                </motion.div>
            )}

            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/95 backdrop-blur-md z-50 flex flex-col"
            >
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900/50">
                    <div className="flex items-center gap-4">
                        <motion.button
                            onClick={onClose}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            className="p-2 text-gray-500 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </motion.button>
                        <div>
                            <h2 className="text-lg font-bold text-white flex items-center gap-2">
                                <Languages className="w-5 h-5 text-fuchsia-500" />
                                Translation Editor
                            </h2>
                            <p className="text-sm text-gray-500">
                                Edit translations before generating audio • {segments.length} segments
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-400">
                            Segment {currentIndex + 1} of {segments.length}
                        </span>
                        <div className="w-32 h-2 bg-gray-800 rounded-full overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-fuchsia-500 to-purple-600"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                </div>

                {/* Main Editor Area */}
                <div className="flex-1 overflow-hidden flex">
                    {/* Segment List (Left Sidebar) */}
                    <div className="w-64 border-r border-gray-800 bg-gray-900/30 overflow-y-auto">
                        <div className="p-3">
                            <h3 className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">
                                All Segments
                            </h3>
                            <div className="space-y-1">
                                {segments.map((seg, idx) => (
                                    <motion.button
                                        key={idx}
                                        onClick={() => goToSegment(idx)}
                                        whileHover={{ scale: 1.02 }}
                                        className={`w-full text-left p-3 rounded-lg transition-colors ${idx === currentIndex
                                            ? 'bg-fuchsia-600/20 border border-fuchsia-500/30'
                                            : 'bg-gray-800/50 hover:bg-gray-800 border border-transparent'
                                            }`}
                                    >
                                        <div className="flex items-center justify-between mb-1">
                                            <span className={`text-xs font-mono ${idx === currentIndex ? 'text-fuchsia-400' : 'text-gray-500'
                                                }`}>
                                                {formatTime(seg.start)}
                                            </span>
                                            {seg.translated_text !== initialSegments[idx]?.translated_text && (
                                                <span className="w-2 h-2 bg-yellow-500 rounded-full" title="Modified" />
                                            )}
                                        </div>
                                        <p className={`text-sm truncate ${idx === currentIndex ? 'text-white' : 'text-gray-400'
                                            }`}>
                                            {seg.original_text.substring(0, 40)}...
                                        </p>
                                    </motion.button>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Editor Panel (Center) */}
                    <div className="flex-1 flex flex-col p-6 overflow-y-auto">
                        {currentSegment && (
                            <motion.div
                                key={currentIndex}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-6 max-w-4xl mx-auto w-full"
                            >
                                {/* Timestamp Badge */}
                                <div className="flex items-center gap-3">
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg">
                                        <Clock className="w-4 h-4 text-fuchsia-500" />
                                        <span className="text-sm font-mono text-gray-300">
                                            {formatTime(currentSegment.start)} → {formatTime(currentSegment.end)}
                                        </span>
                                    </div>
                                    <span className="text-sm text-gray-500">
                                        Duration: {(currentSegment.end - currentSegment.start).toFixed(2)}s
                                    </span>
                                </div>

                                {/* Split View */}
                                <div className="grid grid-cols-2 gap-6">
                                    {/* Original Text (Read-only) */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                                            Original (English)
                                        </label>
                                        <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl min-h-[150px]">
                                            <p className="text-gray-400 leading-relaxed">
                                                {currentSegment.original_text}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Translated Text (Editable) */}
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-fuchsia-400 uppercase tracking-wide flex items-center gap-2">
                                            <Wand2 className="w-4 h-4" />
                                            Translated ({language})
                                        </label>
                                        <textarea
                                            value={currentSegment.translated_text}
                                            onChange={(e) => updateSegment(currentIndex, 'translated_text', e.target.value)}
                                            className="w-full p-4 bg-gray-800 border border-gray-700 rounded-xl min-h-[150px] text-white leading-relaxed resize-none focus:outline-none focus:border-fuchsia-500 focus:ring-1 focus:ring-fuchsia-500 transition-colors"
                                            placeholder="Enter translated text..."
                                        />
                                    </div>
                                </div>

                                {/* Cultural Notes (if any) */}
                                {currentSegment.cultural_notes && (
                                    <div className="p-4 bg-purple-900/20 border border-purple-800/30 rounded-xl">
                                        <h4 className="text-sm font-medium text-purple-400 mb-2 flex items-center gap-2">
                                            <Sparkles className="w-4 h-4" />
                                            Cultural Adaptation Notes
                                        </h4>
                                        <p className="text-sm text-gray-400">
                                            {currentSegment.cultural_notes}
                                        </p>
                                    </div>
                                )}

                                {/* Navigation Buttons */}
                                <div className="flex items-center justify-between pt-4">
                                    <motion.button
                                        onClick={() => goToSegment(currentIndex - 1)}
                                        disabled={currentIndex === 0}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg border border-gray-700 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        <ChevronLeft className="w-4 h-4" />
                                        Previous
                                    </motion.button>

                                    <motion.button
                                        onClick={() => goToSegment(currentIndex + 1)}
                                        disabled={currentIndex === segments.length - 1}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 text-gray-300 rounded-lg border border-gray-700 hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                    >
                                        Next
                                        <ChevronRight className="w-4 h-4" />
                                    </motion.button>
                                </div>
                            </motion.div>
                        )}
                    </div>
                </div>

                {/* Footer - Sticky Save Button */}
                <div className="border-t border-gray-800 bg-gray-900/80 backdrop-blur-sm px-6 py-4">
                    <div className="max-w-4xl mx-auto flex items-center justify-between">
                        <div className="text-sm text-gray-500">
                            {segments.filter((s, i) => s.translated_text !== initialSegments[i]?.translated_text).length} segments modified
                        </div>

                        {error && (
                            <div className="flex items-center gap-2 text-red-400 text-sm">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        {saveSuccess && (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex items-center gap-2 text-green-400 text-sm"
                            >
                                <CheckCircle className="w-4 h-4" />
                                Dubbing started! Redirecting...
                            </motion.div>
                        )}

                        <motion.button
                            onClick={handleFinalize}
                            disabled={isSaving || saveSuccess}
                            whileHover={{ scale: 1.05, boxShadow: '0 0 30px rgba(168, 85, 247, 0.4)' }}
                            whileTap={{ scale: 0.95 }}
                            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-fuchsia-600 to-purple-600 text-white font-bold rounded-xl disabled:opacity-50 transition-all"
                        >
                            {isSaving ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Starting Dubbing...
                                </>
                            ) : (
                                <>
                                    <Save className="w-5 h-5" />
                                    Save & Generate Audio
                                </>
                            )}
                        </motion.button>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
