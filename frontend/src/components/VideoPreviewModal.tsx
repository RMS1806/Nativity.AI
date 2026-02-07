'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Download, Play, Volume2, VolumeX } from 'lucide-react';

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
    fileName
}: VideoPreviewModalProps) {
    const [showOriginal, setShowOriginal] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const localizedVideoRef = useRef<HTMLVideoElement>(null);
    const originalVideoRef = useRef<HTMLVideoElement>(null);

    // Sync time between videos when toggling
    const handleToggle = () => {
        const activeVideo = showOriginal ? originalVideoRef.current : localizedVideoRef.current;
        const nextVideo = showOriginal ? localizedVideoRef.current : originalVideoRef.current;

        if (activeVideo && nextVideo) {
            const time = activeVideo.currentTime;
            setCurrentTime(time);
            nextVideo.currentTime = time;

            // If active video was playing, pause it and play the next
            if (!activeVideo.paused) {
                activeVideo.pause();
                nextVideo.play().catch(() => { });
            }
        }

        setShowOriginal(!showOriginal);
    };

    // Reset state when modal closes
    useEffect(() => {
        if (!isOpen) {
            setShowOriginal(false);
            setCurrentTime(0);
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const currentUrl = showOriginal && originalVideoUrl ? originalVideoUrl : localizedVideoUrl;
    const hasOriginal = !!originalVideoUrl;

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/90 backdrop-blur-md z-50 flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                    className="bg-gray-900 border border-gray-800 rounded-2xl shadow-2xl max-w-4xl w-full overflow-hidden"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header with Magic Compare Toggle */}
                    <div className="flex items-center justify-between p-4 border-b border-gray-800">
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <Play className="w-5 h-5 text-fuchsia-500" />
                                <span className="text-white font-medium truncate max-w-[200px]">{fileName}</span>
                            </div>

                            {/* Magic Compare Toggle */}
                            {hasOriginal && (
                                <div className="flex items-center gap-2 ml-4">
                                    <span className={`text-sm font-medium transition-colors ${!showOriginal ? 'text-fuchsia-400' : 'text-gray-500'}`}>
                                        Localized
                                    </span>
                                    <motion.button
                                        onClick={handleToggle}
                                        className="relative w-14 h-7 rounded-full bg-gray-800 border border-gray-700 p-1 cursor-pointer"
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                    >
                                        <motion.div
                                            className="w-5 h-5 rounded-full bg-gradient-to-r from-fuchsia-500 to-purple-600 shadow-lg"
                                            animate={{ x: showOriginal ? 24 : 0 }}
                                            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                                        />
                                    </motion.button>
                                    <span className={`text-sm font-medium transition-colors ${showOriginal ? 'text-purple-400' : 'text-gray-500'}`}>
                                        Original
                                    </span>
                                </div>
                            )}
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

                    {/* Video Player Area */}
                    <div className="relative bg-black aspect-video">
                        {/* Badge showing current version */}
                        <motion.div
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            key={showOriginal ? 'original' : 'localized'}
                            className="absolute top-4 left-4 z-10"
                        >
                            <span className={`px-3 py-1.5 rounded-full text-xs font-bold backdrop-blur-sm ${showOriginal
                                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                    : 'bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/30'
                                }`}>
                                {showOriginal ? '🎬 Original Audio' : '✨ AI Localized'}
                            </span>
                        </motion.div>

                        {/* Localized Video (shown by default) */}
                        <video
                            ref={localizedVideoRef}
                            controls
                            autoPlay={!showOriginal}
                            className={`w-full h-full ${showOriginal ? 'hidden' : 'block'}`}
                            src={localizedVideoUrl}
                        />

                        {/* Original Video (hidden by default) */}
                        {originalVideoUrl && (
                            <video
                                ref={originalVideoRef}
                                controls
                                autoPlay={showOriginal}
                                className={`w-full h-full ${showOriginal ? 'block' : 'hidden'}`}
                                src={originalVideoUrl}
                            />
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex items-center justify-between p-4 border-t border-gray-800 bg-gray-900/50">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <Volume2 className="w-4 h-4" />
                            <span>{showOriginal ? 'Playing original audio' : 'Playing localized audio'}</span>
                        </div>

                        <motion.a
                            href={currentUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            whileHover={{ scale: 1.05, boxShadow: '0 0 25px rgba(168, 85, 247, 0.4)' }}
                            whileTap={{ scale: 0.95 }}
                            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-fuchsia-600 to-purple-600 text-white font-bold rounded-lg text-sm"
                        >
                            <Download className="w-4 h-4" />
                            Download {showOriginal ? 'Original' : 'Localized'}
                        </motion.a>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
