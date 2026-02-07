'use client';

import { motion } from 'framer-motion';
import { Brain, Mic, Film, CheckCircle, Loader2, CloudUpload } from 'lucide-react';
import { JobStatus } from '@/types';

interface ProcessingStatusProps {
    status: JobStatus;
    progress: number;
    message: string;
}

const stages = [
    {
        id: 'uploading',
        label: 'Uploading',
        description: 'Sending video to cloud',
        icon: CloudUpload,
        statuses: ['uploading'],
    },
    {
        id: 'analyzing',
        label: 'Gemini Analysis',
        description: 'Understanding context & culture',
        icon: Brain,
        statuses: ['analyzing'],
    },
    {
        id: 'generating_audio',
        label: 'Voice Generation',
        description: 'Creating localized audio',
        icon: Mic,
        statuses: ['generating_audio'],
    },
    {
        id: 'stitching',
        label: 'Video Stitching',
        description: 'Merging audio with video',
        icon: Film,
        statuses: ['stitching'],
    },
];

export default function ProcessingStatus({ status, progress, message }: ProcessingStatusProps) {
    const getStageState = (stage: typeof stages[0]): 'pending' | 'active' | 'complete' => {
        const stageIndex = stages.findIndex(s => s.id === stage.id);
        const currentIndex = stages.findIndex(s => s.statuses.includes(status));

        if (status === 'complete') return 'complete';
        if (stageIndex < currentIndex) return 'complete';
        if (stageIndex === currentIndex) return 'active';
        return 'pending';
    };

    return (
        <div className="w-full max-w-2xl mx-auto py-8">
            {/* Main Progress Bar */}
            <div className="mb-8">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-600">Overall Progress</span>
                    <span className="text-sm font-bold text-blue-600">{progress}%</span>
                </div>
                <div className="w-full h-3 bg-gray-200 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
            </div>

            {/* Status Message */}
            <motion.div
                key={message}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-8"
            >
                <p className="text-lg font-medium text-gray-800">{message}</p>
            </motion.div>

            {/* Stage Steps */}
            <div className="space-y-4">
                {stages.map((stage, index) => {
                    const state = getStageState(stage);
                    const Icon = stage.icon;

                    return (
                        <motion.div
                            key={stage.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className={`
                flex items-center gap-4 p-4 rounded-xl transition-all duration-300
                ${state === 'active' ? 'bg-blue-50 border-2 border-blue-200 shadow-md' : ''}
                ${state === 'complete' ? 'bg-green-50 border border-green-200' : ''}
                ${state === 'pending' ? 'bg-gray-50 border border-gray-200 opacity-50' : ''}
              `}
                        >
                            {/* Icon */}
                            <div className={`
                w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0
                ${state === 'active' ? 'bg-blue-500' : ''}
                ${state === 'complete' ? 'bg-green-500' : ''}
                ${state === 'pending' ? 'bg-gray-300' : ''}
              `}>
                                {state === 'active' ? (
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                    >
                                        <Loader2 className="w-6 h-6 text-white" />
                                    </motion.div>
                                ) : state === 'complete' ? (
                                    <CheckCircle className="w-6 h-6 text-white" />
                                ) : (
                                    <Icon className="w-6 h-6 text-white" />
                                )}
                            </div>

                            {/* Text */}
                            <div className="flex-1">
                                <h3 className={`font-semibold ${state === 'active' ? 'text-blue-800' : state === 'complete' ? 'text-green-800' : 'text-gray-600'}`}>
                                    {stage.label}
                                </h3>
                                <p className={`text-sm ${state === 'active' ? 'text-blue-600' : state === 'complete' ? 'text-green-600' : 'text-gray-400'}`}>
                                    {stage.description}
                                </p>
                            </div>

                            {/* Status Badge */}
                            {state === 'active' && (
                                <motion.div
                                    className="px-3 py-1 bg-blue-500 text-white text-xs font-bold rounded-full"
                                    animate={{ scale: [1, 1.05, 1] }}
                                    transition={{ duration: 1.5, repeat: Infinity }}
                                >
                                    ACTIVE
                                </motion.div>
                            )}
                            {state === 'complete' && (
                                <div className="px-3 py-1 bg-green-500 text-white text-xs font-bold rounded-full">
                                    DONE
                                </div>
                            )}
                        </motion.div>
                    );
                })}
            </div>

            {/* Animated Background Effect */}
            <motion.div
                className="fixed inset-0 pointer-events-none z-0"
                style={{
                    background: 'radial-gradient(circle at 50% 50%, rgba(59, 130, 246, 0.05) 0%, transparent 50%)',
                }}
                animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 0.8, 0.5],
                }}
                transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: 'easeInOut',
                }}
            />
        </div>
    );
}
