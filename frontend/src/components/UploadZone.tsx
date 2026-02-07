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
            {/* Pure Dark Upload Zone */}
            <motion.div
                className={`
                    relative border-2 border-dashed rounded-2xl p-12 text-center
                    bg-gray-900
                    transition-all duration-300 cursor-pointer
                    ${isDragging
                        ? 'border-fuchsia-500 bg-fuchsia-900/10'
                        : 'border-gray-700 hover:border-fuchsia-600/50 hover:bg-gray-800/50'
                    }
                    ${isUploading ? 'pointer-events-none opacity-75' : ''}
                `}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                whileHover={{ scale: isUploading ? 1 : 1.01 }}
                whileTap={{ scale: isUploading ? 1 : 0.99 }}
            >
                <input
                    type="file"
                    accept="video/*"
                    onChange={handleInputChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    disabled={isUploading}
                />

                <AnimatePresence mode="wait">
                    {isUploading ? (
                        <motion.div
                            key="uploading"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <motion.div
                                className="w-16 h-16 mx-auto rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center"
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                            >
                                <Upload className="w-8 h-8 text-fuchsia-500" />
                            </motion.div>
                            <div>
                                <p className="text-lg font-bold text-white">Uploading to cloud...</p>
                                <p className="text-sm text-gray-500">{selectedFile?.name}</p>
                            </div>
                            <div className="w-full max-w-xs mx-auto bg-gray-800 rounded-full h-3 overflow-hidden">
                                <motion.div
                                    className="h-full bg-gradient-to-r from-fuchsia-500 to-purple-600 rounded-full"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${uploadProgress}%` }}
                                    transition={{ duration: 0.3 }}
                                />
                            </div>
                            <p className="text-sm font-bold text-fuchsia-500">{uploadProgress}%</p>
                        </motion.div>
                    ) : selectedFile ? (
                        <motion.div
                            key="selected"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <div className="w-16 h-16 mx-auto rounded-full bg-green-900/30 border border-green-800 flex items-center justify-center">
                                <CheckCircle className="w-8 h-8 text-green-400" />
                            </div>
                            <div>
                                <p className="text-lg font-bold text-white">Ready to process</p>
                                <p className="text-sm text-gray-400">{selectedFile.name}</p>
                                <p className="text-xs text-gray-600">{formatFileSize(selectedFile.size)}</p>
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="idle"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="space-y-4"
                        >
                            <motion.div
                                className="w-20 h-20 mx-auto rounded-full bg-gray-800 border border-gray-700 flex items-center justify-center"
                                animate={{ y: [0, -5, 0] }}
                                transition={{ duration: 2, repeat: Infinity }}
                            >
                                <Film className="w-10 h-10 text-fuchsia-500" />
                            </motion.div>
                            <div>
                                <p className="text-xl font-bold text-white">
                                    Drop your video here
                                </p>
                                <p className="text-gray-400 mt-1">
                                    or <span className="text-fuchsia-500 font-medium">browse</span> to upload
                                </p>
                            </div>
                            <p className="text-xs text-gray-600">
                                MP4, MOV, WebM • Max 500MB
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>

            {/* Error Message */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mt-4 p-4 bg-red-900/30 border border-red-800 rounded-xl flex items-center gap-3"
                    >
                        <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                        <p className="text-sm text-red-400">{error}</p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
