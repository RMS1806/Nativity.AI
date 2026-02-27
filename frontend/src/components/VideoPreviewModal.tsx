'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Play, Volume2 } from 'lucide-react';

interface VideoPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    localizedVideoUrl: string;
    originalVideoUrl?: string;
    fileName: string;
}

export default function VideoPreviewModal({
    isOpen,
    onClose,
    localizedVideoUrl,
    originalVideoUrl,
    fileName,
}: VideoPreviewModalProps) {
    // false = localized, true = original
    const [showOriginal, setShowOriginal] = useState(false);
    const localizedVideoRef = useRef<HTMLVideoElement>(null);
    const originalVideoRef = useRef<HTMLVideoElement>(null);

    // Sync playback position when toggling
    const handleToggle = () => {
        const activeRef = showOriginal ? originalVideoRef : localizedVideoRef;
        const nextRef = showOriginal ? localizedVideoRef : originalVideoRef;

        if (activeRef.current && nextRef.current) {
            const time = activeRef.current.currentTime;
            nextRef.current.currentTime = time;
            if (!activeRef.current.paused) {
                activeRef.current.pause();
                nextRef.current.play().catch(() => { });
            }
        }

        setShowOriginal((prev) => !prev);
    };

    // Reset when modal closes
    useEffect(() => {
        if (!isOpen) {
            setShowOriginal(false);
            if (localizedVideoRef.current) localizedVideoRef.current.pause();
            if (originalVideoRef.current) originalVideoRef.current.pause();
        }
    }, [isOpen]);

    // Close on Escape key
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        if (isOpen) window.addEventListener('keydown', handleKey);
        return () => window.removeEventListener('keydown', handleKey);
    }, [isOpen, onClose]);

    const hasOriginal = !!originalVideoUrl;
    const currentUrl =
        showOriginal && originalVideoUrl ? originalVideoUrl : localizedVideoUrl;

    return (
        <AnimatePresence>
            {isOpen && (
                /* ── Full-screen overlay ───────────────────────────── */
                <motion.div
                    key="vpm-overlay"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    style={{
                        background: 'rgba(0,0,0,0.9)',
                        backdropFilter: 'blur(16px)',
                        WebkitBackdropFilter: 'blur(16px)',
                    }}
                    onClick={onClose}
                >
                    {/* ── Modal container ──────────────────────────── */}
                    <motion.div
                        key="vpm-container"
                        initial={{ opacity: 0, scale: 0.85, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.85, y: 30 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="relative w-full max-w-4xl rounded-2xl overflow-hidden"
                        style={{
                            background: 'rgba(8,8,18,0.97)',
                            border: '1px solid rgba(255,255,255,0.10)',
                            boxShadow: '0 0 60px rgba(0,229,255,0.08), 0 0 120px rgba(255,0,255,0.04)',
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* ── Header ───────────────────────────────── */}
                        <div
                            className="flex items-center justify-between px-5 py-4"
                            style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
                        >
                            {/* Left: file name + badge */}
                            <div className="flex items-center gap-3 min-w-0">
                                <div
                                    className="p-2 rounded-lg flex-shrink-0"
                                    style={{
                                        background: 'rgba(0,229,255,0.08)',
                                        border: '1px solid rgba(0,229,255,0.2)',
                                    }}
                                >
                                    <Play className="w-4 h-4" style={{ color: '#00E5FF' }} />
                                </div>
                                <span
                                    className="font-semibold text-white truncate max-w-[260px] text-sm"
                                    title={fileName}
                                >
                                    {fileName}
                                </span>
                            </div>

                            {/* Centre: Original / Localized toggle */}
                            {hasOriginal && (
                                <div className="flex items-center gap-3 mx-4">
                                    {/* Localized label */}
                                    <span
                                        className="text-xs font-bold uppercase tracking-widest transition-colors"
                                        style={{
                                            color: !showOriginal ? '#CCFF00' : 'rgba(255,255,255,0.3)',
                                        }}
                                    >
                                        Localized
                                    </span>

                                    {/* Toggle pill */}
                                    <motion.button
                                        onClick={handleToggle}
                                        className="relative w-14 h-7 rounded-full p-1 cursor-pointer flex-shrink-0"
                                        style={{
                                            background: 'rgba(255,255,255,0.07)',
                                            border: '1px solid rgba(255,255,255,0.12)',
                                        }}
                                        whileTap={{ scale: 0.95 }}
                                        aria-label="Toggle between Localized and Original video"
                                    >
                                        <motion.div
                                            className="w-5 h-5 rounded-full shadow-lg"
                                            style={{
                                                background: showOriginal
                                                    ? 'linear-gradient(135deg, #00E5FF, #FF00FF)'
                                                    : 'linear-gradient(135deg, #CCFF00, #00E5FF)',
                                            }}
                                            animate={{ x: showOriginal ? 26 : 0 }}
                                            transition={{
                                                type: 'spring',
                                                stiffness: 500,
                                                damping: 30,
                                            }}
                                        />
                                    </motion.button>

                                    {/* Original label */}
                                    <span
                                        className="text-xs font-bold uppercase tracking-widest transition-colors"
                                        style={{
                                            color: showOriginal ? '#00E5FF' : 'rgba(255,255,255,0.3)',
                                        }}
                                    >
                                        Original
                                    </span>
                                </div>
                            )}

                            {/* Right: close button */}
                            <motion.button
                                onClick={onClose}
                                whileHover={{ scale: 1.1, rotate: 90 }}
                                whileTap={{ scale: 0.9 }}
                                className="p-2 rounded-lg transition-colors flex-shrink-0"
                                style={{
                                    background: 'rgba(255,255,255,0.05)',
                                    border: '1px solid rgba(255,255,255,0.08)',
                                    color: '#6b7280',
                                }}
                                title="Close"
                                aria-label="Close video player"
                            >
                                <X className="w-5 h-5" />
                            </motion.button>
                        </div>

                        {/* ── Video Player Area ─────────────────────── */}
                        <div className="relative bg-black aspect-video">
                            {/* Version badge */}
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={showOriginal ? 'badge-original' : 'badge-localized'}
                                    initial={{ opacity: 0, y: -8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute top-3 left-3 z-10"
                                >
                                    <span
                                        className="px-3 py-1.5 rounded-full text-xs font-bold backdrop-blur-sm"
                                        style={
                                            showOriginal
                                                ? {
                                                    background: 'rgba(0,229,255,0.12)',
                                                    border: '1px solid rgba(0,229,255,0.3)',
                                                    color: '#00E5FF',
                                                }
                                                : {
                                                    background: 'rgba(204,255,0,0.12)',
                                                    border: '1px solid rgba(204,255,0,0.35)',
                                                    color: '#CCFF00',
                                                }
                                        }
                                    >
                                        {showOriginal ? '🎬 Original Audio' : '✨ AI Localized'}
                                    </span>
                                </motion.div>
                            </AnimatePresence>

                            {/* Localized video */}
                            <video
                                ref={localizedVideoRef}
                                controls
                                autoPlay={!showOriginal}
                                className={`w-full h-full rounded-none ${showOriginal ? 'hidden' : 'block'}`}
                                src={localizedVideoUrl}
                                preload="metadata"
                            />

                            {/* Original video */}
                            {originalVideoUrl && (
                                <video
                                    ref={originalVideoRef}
                                    controls
                                    autoPlay={showOriginal}
                                    className={`w-full h-full rounded-none ${showOriginal ? 'block' : 'hidden'}`}
                                    src={originalVideoUrl}
                                    preload="metadata"
                                />
                            )}
                        </div>

                        {/* ── Footer ───────────────────────────────── */}
                        <div
                            className="flex items-center justify-between px-5 py-3"
                            style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
                        >
                            <div className="flex items-center gap-2 text-xs text-gray-500">
                                <Volume2 className="w-4 h-4" />
                                <span>
                                    {showOriginal
                                        ? 'Playing original audio'
                                        : 'Playing AI-localized audio'}
                                </span>
                            </div>

                            <motion.a
                                href={currentUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                whileHover={{
                                    scale: 1.05,
                                    boxShadow: '0 0 25px rgba(0,229,255,0.35)',
                                }}
                                whileTap={{ scale: 0.95 }}
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all"
                                style={{
                                    background: 'rgba(0,229,255,0.1)',
                                    border: '1px solid rgba(0,229,255,0.3)',
                                    color: '#00E5FF',
                                }}
                            >
                                <Download className="w-3.5 h-3.5" />
                                Download {showOriginal ? 'Original' : 'Localized'}
                            </motion.a>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
