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

    return (
        <div className="w-full max-w-2xl mx-auto">
            <motion.div
                className={`relative p-12 text-center cursor-pointer overflow-hidden transition-all duration-200 group ${isDragging ? 'neo-border' : 'upload-dashed-border'}`}
                style={{
                    backgroundColor: isDragging ? '#d8e2ff' : selectedFile ? '#F3EDFF' : '#FFFFFF',
                    boxShadow: isDragging ? '4px 4px 0px 0px #1A1A1A' : 'none',
                    borderRadius: '0.5rem',
                }}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                animate={isDragging ? { scale: 1.02 } : { scale: 1 }}
                whileHover={!isUploading && !isDragging ? { x: -2, y: -2 } : {}}
            >
                <input
                    type="file"
                    accept="video/*"
                    onChange={handleInputChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={isUploading}
                />

                <AnimatePresence mode="wait">
                    {/* ── Uploading State ─────────────── */}
                    {isUploading ? (
                        <motion.div
                            key="uploading"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-6"
                        >
                            <div className="flex flex-col items-center gap-4">
                                <div className="w-20 h-20 mx-auto neo-border neo-shadow flex items-center justify-center bg-white animate-neo-spin">
                                    <Upload className="w-8 h-8 text-[#8127cf]" />
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-[#1A1A1A] font-headline tracking-wide">
                                        Uploading to Cloud
                                    </p>
                                    <p className="text-sm text-[#5c403d] mt-1 font-mono-label">{selectedFile?.name}</p>
                                </div>
                            </div>

                            {/* Neo Brutal Progress Bar */}
                            <div className="w-full max-w-xs mx-auto">
                                <div className="flex justify-between items-end mb-2">
                                    <span className="font-mono-label text-[#5c403d] uppercase tracking-wider text-xs">Uploading</span>
                                    <span className="font-headline text-xl font-bold text-[#ba061b]">{uploadProgress}%</span>
                                </div>
                                <div
                                    className="h-6 w-full neo-border overflow-hidden"
                                    style={{ backgroundColor: '#eee7df', borderRadius: '9999px' }}
                                >
                                    <motion.div
                                        className="h-full"
                                        style={{
                                            backgroundColor: '#FBBF24',
                                            borderRight: uploadProgress > 0 && uploadProgress < 100 ? '3px solid #1A1A1A' : 'none',
                                        }}
                                        initial={{ width: 0 }}
                                        animate={{ width: `${uploadProgress}%` }}
                                        transition={{ duration: 0.3 }}
                                    />
                                </div>
                            </div>
                        </motion.div>

                    ) : selectedFile ? (
                        /* ── File Selected State ─────────── */
                        <motion.div
                            key="selected"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <div
                                className="w-16 h-16 mx-auto neo-border neo-shadow flex items-center justify-center"
                                style={{ backgroundColor: '#BFFF00' }}
                            >
                                <CheckCircle className="w-8 h-8 text-[#1A1A1A]" />
                            </div>
                            <div>
                                <p className="text-lg font-bold text-[#1A1A1A] font-headline">Ready to process</p>
                                <p className="text-sm text-[#5c403d] mt-1 font-mono-label">{selectedFile.name}</p>
                                <p className="text-xs text-[#906f6c] mt-0.5 font-mono-label">{formatFileSize(selectedFile.size)}</p>
                            </div>
                        </motion.div>

                    ) : (
                        /* ── Idle / Default State ──────────── */
                        <motion.div
                            key="idle"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <div className="float-y">
                                <Film className="w-20 h-20 mx-auto text-[#8127cf]" />
                            </div>
                            <div>
                                <p className="text-2xl font-bold text-[#1A1A1A] font-headline">
                                    {isDragging ? 'Drop it!' : 'Drop your video here'}
                                </p>
                                <p className="text-[#5c403d] mt-2">
                                    or{' '}
                                    <span className="font-bold text-[#0058be] underline decoration-[3px] underline-offset-4">
                                        browse
                                    </span>{' '}
                                    to upload
                                </p>
                            </div>
                            <p className="font-mono-label text-[#906f6c] text-xs">MP4, MOV, WebM • Max 500MB</p>
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
                        className="mt-4 p-4 neo-border flex items-center gap-3"
                        style={{ backgroundColor: '#FF2D78', color: 'white' }}
                    >
                        <AlertCircle className="w-5 h-5 flex-shrink-0" />
                        <p className="text-sm font-bold">{error}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
