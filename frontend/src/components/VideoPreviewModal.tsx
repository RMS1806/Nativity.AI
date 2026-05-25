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
                    style={{ background: 'rgba(0,0,0,0.8)' }}
                    onClick={onClose}
                >
                    {/* ── Modal container ──────────────────────────── */}
                    <motion.div
                        key="vpm-container"
                        initial={{ opacity: 0, scale: 0.85, y: 30 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.85, y: 30 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="relative w-full max-w-4xl bg-white neo-border neo-shadow-lg"
                        onClick={(e) => e.stopPropagation()}
                    >
                        {/* ── Header ───────────────────────────────── */}
                        <div
                            className="flex items-center justify-between px-5 py-4 bg-[#f4ede5]"
                            style={{ borderBottom: '3px solid #1A1A1A' }}
                        >
                            {/* Left: file name + badge */}
                            <div className="flex items-center gap-3 min-w-0">
                                <div
                                    className="p-2 flex-shrink-0 bg-white neo-border"
                                    style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                                >
                                    <Play className="w-4 h-4 text-[#ba061b]" />
                                </div>
                                <span
                                    className="font-bold text-[#1A1A1A] font-headline truncate max-w-[260px] text-lg"
                                    title={fileName}
                                >
                                    {fileName}
                                </span>
                            </div>

                            {/* Centre: Original / Localized toggle */}
                            {hasOriginal && (
                                <div className="flex items-center gap-3 mx-4 bg-white neo-border p-1" style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}>
                                    <button
                                        onClick={() => showOriginal && handleToggle()}
                                        className={`px-3 py-1 font-mono-label text-xs font-bold uppercase transition-colors ${!showOriginal ? 'bg-[#BFFF00] neo-border text-[#1A1A1A]' : 'text-[#5c403d] hover:text-[#1A1A1A]'}`}
                                    >
                                        Localized
                                    </button>
                                    <button
                                        onClick={() => !showOriginal && handleToggle()}
                                        className={`px-3 py-1 font-mono-label text-xs font-bold uppercase transition-colors ${showOriginal ? 'bg-[#FF2D78] neo-border text-white' : 'text-[#5c403d] hover:text-[#1A1A1A]'}`}
                                    >
                                        Original
                                    </button>
                                </div>
                            )}

                            {/* Right: close button */}
                            <motion.button
                                onClick={onClose}
                                whileHover={{ scale: 1.1, rotate: 90 }}
                                whileTap={{ scale: 0.9 }}
                                className="p-2 bg-white neo-border text-[#1A1A1A] transition-colors flex-shrink-0"
                                style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                                title="Close"
                                aria-label="Close video player"
                            >
                                <X className="w-5 h-5" />
                            </motion.button>
                        </div>

                        {/* ── Video Player Area ─────────────────────── */}
                        <div className="relative bg-black aspect-video border-b-4 border-[#1A1A1A]">
                            {/* Version badge */}
                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={showOriginal ? 'badge-original' : 'badge-localized'}
                                    initial={{ opacity: 0, y: -8 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -8 }}
                                    transition={{ duration: 0.15 }}
                                    className="absolute top-4 left-4 z-10"
                                >
                                    <span
                                        className="px-4 py-2 font-mono-label text-xs font-bold uppercase neo-border"
                                        style={
                                            showOriginal
                                                ? { background: '#FF2D78', color: 'white', boxShadow: '2px 2px 0px 0px #1A1A1A' }
                                                : { background: '#BFFF00', color: '#1A1A1A', boxShadow: '2px 2px 0px 0px #1A1A1A' }
                                        }
                                    >
                                        {showOriginal ? 'Original Audio' : 'AI Localized'}
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
                            className="flex items-center justify-between px-5 py-4 bg-white"
                        >
                            <div className="flex items-center gap-2 font-mono-label text-sm text-[#5c403d] font-bold">
                                <Volume2 className="w-5 h-5" />
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
                                whileHover={{ y: -2, x: -2 }}
                                whileTap={{ y: 2, x: 2 }}
                                className="inline-flex items-center gap-2 px-6 py-3 font-mono-label font-bold uppercase text-white bg-[#0058be] neo-border transition-all"
                                style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}
                            >
                                <Download className="w-4 h-4" />
                                Download {showOriginal ? 'Original' : 'Localized'}
                            </motion.a>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
