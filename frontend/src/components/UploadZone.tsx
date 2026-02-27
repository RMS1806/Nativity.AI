'use client';

import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Film, CheckCircle, AlertCircle } from 'lucide-react';

interface UploadZoneProps {
    onFileSelect: (file: File) => void;
    isUploading: boolean;
    uploadProgress: number;
}

export default function UploadZone({ onFileSelect, isUploading, uploadProgress }: UploadZoneProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [error, setError] = useState<string | null>(null);

    const validateFile = (file: File): boolean => {
        if (!file.type.startsWith('video/')) {
            setError('Please upload a video file (MP4, MOV, etc.)');
            return false;
        }
        if (file.size > 500 * 1024 * 1024) {
            setError('File size must be under 500MB');
            return false;
        }
        setError(null);
        return true;
    };

    const handleFile = useCallback((file: File) => {
        if (validateFile(file)) {
            setSelectedFile(file);
            onFileSelect(file);
        }
    }, [onFileSelect]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
    }, [handleFile]);

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) handleFile(file);
    }, [handleFile]);

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    // Determine state-driven styles
    const borderColor = isDragging
        ? '#FF00FF'
        : selectedFile
            ? 'rgba(204,255,0,0.5)'
            : 'rgba(0,229,255,0.25)';

    const boxShadow = isDragging
        ? '0 0 60px rgba(255,0,255,0.35), inset 0 0 30px rgba(255,0,255,0.05)'
        : selectedFile
            ? '0 0 30px rgba(204,255,0,0.15)'
            : 'none';

    return (
        <div className="w-full max-w-2xl mx-auto">
            <motion.div
                className="relative rounded-2xl p-12 text-center cursor-pointer overflow-hidden"
                style={{
                    background: 'rgba(255,255,255,0.04)',
                    backdropFilter: 'blur(16px)',
                    WebkitBackdropFilter: 'blur(16px)',
                    border: `2px ${isDragging ? 'solid' : 'dashed'} ${borderColor}`,
                    boxShadow,
                    transition: 'border-color 0.25s, box-shadow 0.35s',
                }}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                animate={isDragging ? { scale: 1.02 } : { scale: 1 }}
                whileHover={!isUploading && !isDragging ? { scale: 1.01 } : {}}
                whileTap={!isUploading ? { scale: 0.99 } : {}}
            >
                {/* Shimmer overlay */}
                {!isDragging && !isUploading && (
                    <span className="shimmer-overlay" style={{ opacity: 0.6 }} />
                )}

                <input
                    type="file"
                    accept="video/*"
                    onChange={handleInputChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={isUploading}
                />

                <AnimatePresence mode="wait">
                    {/* ── Uploading / AI Processing State ─────────────── */}
                    {isUploading ? (
                        <motion.div
                            key="uploading"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-6"
                        >
                            {/* Spinning conic-gradient border orb */}
                            <div className="flex flex-col items-center gap-4">
                                <div
                                    className="border-spin-wrapper w-20 h-20 mx-auto rounded-full"
                                >
                                    <div className="border-spin-inner w-full h-full rounded-full flex items-center justify-center">
                                        <Upload
                                            className="w-8 h-8"
                                            style={{ color: '#00E5FF' }}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-white tracking-wide">
                                        Uploading to Cloud
                                    </p>
                                    <p className="text-sm text-gray-500 mt-1">{selectedFile?.name}</p>
                                </div>
                            </div>

                            {/* Progress bar */}
                            <div
                                className="w-full max-w-xs mx-auto rounded-full h-2 overflow-hidden"
                                style={{ background: 'rgba(255,255,255,0.08)' }}
                            >
                                <motion.div
                                    className="h-full rounded-full"
                                    style={{
                                        background: 'linear-gradient(90deg, #00E5FF, #FF00FF)',
                                        boxShadow: '0 0 12px rgba(0,229,255,0.6)',
                                    }}
                                    initial={{ width: 0 }}
                                    animate={{ width: `${uploadProgress}%` }}
                                    transition={{ duration: 0.3 }}
                                />
                            </div>
                            <p className="text-sm font-bold" style={{ color: '#00E5FF' }}>
                                {uploadProgress}%
                            </p>
                        </motion.div>

                    ) : selectedFile ? (
                        /* ── File Selected State ─────────────────────────── */
                        <motion.div
                            key="selected"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <div
                                className="w-16 h-16 mx-auto rounded-full flex items-center justify-center"
                                style={{
                                    background: 'rgba(204,255,0,0.08)',
                                    border: '1px solid rgba(204,255,0,0.4)',
                                }}
                            >
                                <CheckCircle className="w-8 h-8" style={{ color: '#CCFF00' }} />
                            </div>
                            <div>
                                <p className="text-lg font-bold text-white">Ready to process</p>
                                <p className="text-sm text-gray-400 mt-1">{selectedFile.name}</p>
                                <p className="text-xs text-gray-600 mt-0.5">{formatFileSize(selectedFile.size)}</p>
                            </div>
                        </motion.div>

                    ) : (
                        /* ── Idle / Default State ────────────────────────── */
                        <motion.div
                            key="idle"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <motion.div
                                className="w-20 h-20 mx-auto rounded-full flex items-center justify-center float-y"
                                style={{
                                    background: 'rgba(0,229,255,0.08)',
                                    border: '1px solid rgba(0,229,255,0.25)',
                                }}
                            >
                                <Film className="w-10 h-10" style={{ color: '#00E5FF' }} />
                            </motion.div>
                            <div>
                                <p className="text-xl font-bold text-white">
                                    {isDragging ? 'Drop it!' : 'Drop your video here'}
                                </p>
                                <p className="text-gray-400 mt-1">
                                    or{' '}
                                    <span className="font-medium" style={{ color: '#00E5FF' }}>
                                        browse
                                    </span>{' '}
                                    to upload
                                </p>
                            </div>
                            <p className="text-xs text-gray-600">MP4, MOV, WebM • Max 500MB</p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* Error */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mt-4 p-4 rounded-xl flex items-center gap-3"
                        style={{
                            background: 'rgba(255,60,60,0.08)',
                            border: '1px solid rgba(255,60,60,0.3)',
                        }}
                    >
                        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                        <p className="text-sm text-red-400">{error}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
