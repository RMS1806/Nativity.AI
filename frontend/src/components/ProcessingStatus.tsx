'use client';

import { motion } from 'framer-motion';
import { Brain, Mic, Film, CheckCircle, Zap, CloudUpload } from 'lucide-react';
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

            {/* ── Pulsing Orb Header ──────────────────────────────── */}
            <div className="flex flex-col items-center mb-10">
                <div className="border-spin-wrapper w-24 h-24 rounded-full mb-4">
                    <div className="border-spin-inner w-full h-full rounded-full flex items-center justify-center"
                        style={{ background: 'rgba(0,229,255,0.05)' }}
                    >
                        <Zap className="w-10 h-10" style={{ color: '#00E5FF' }} />
                    </div>
                </div>
                <motion.p
                    key={message}
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-lg font-semibold text-white text-center"
                >
                    {message || 'Processing…'}
                </motion.p>
                <p className="text-sm text-gray-500 mt-1">AI is working on your video</p>
            </div>

            {/* ── Overall Progress Bar ────────────────────────────── */}
            <div className="mb-8">
                <div className="flex justify-between items-center mb-2">
                    <span className="text-sm font-medium text-gray-500">Overall Progress</span>
                    <span className="text-sm font-bold" style={{ color: '#00E5FF' }}>
                        {progress}%
                    </span>
                </div>
                <div
                    className="w-full h-2 rounded-full overflow-hidden"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    <motion.div
                        className="h-full rounded-full"
                        style={{
                            background: 'linear-gradient(90deg, #00E5FF, #FF00FF)',
                            boxShadow: '0 0 12px rgba(0,229,255,0.5)',
                        }}
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
            </div>

            {/* ── Stage Steps ─────────────────────────────────────── */}
            <div className="space-y-3">
                {stages.map((stage, index) => {
                    const state = getStageState(stage);
                    const Icon = stage.icon;

                    const borderStyle =
                        state === 'active'
                            ? '1px solid rgba(0,229,255,0.5)'
                            : state === 'complete'
                                ? '1px solid rgba(204,255,0,0.35)'
                                : '1px solid rgba(255,255,255,0.07)';

                    const bgStyle =
                        state === 'active'
                            ? 'rgba(0,229,255,0.05)'
                            : state === 'complete'
                                ? 'rgba(204,255,0,0.04)'
                                : 'rgba(255,255,255,0.02)';

                    const iconBg =
                        state === 'active'
                            ? 'rgba(0,229,255,0.15)'
                            : state === 'complete'
                                ? 'rgba(204,255,0,0.15)'
                                : 'rgba(255,255,255,0.05)';

                    const iconColor =
                        state === 'active'
                            ? '#00E5FF'
                            : state === 'complete'
                                ? '#CCFF00'
                                : '#4b5563';

                    return (
                        <motion.div
                            key={stage.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: state === 'pending' ? 0.4 : 1, x: 0 }}
                            transition={{ delay: index * 0.08 }}
                            className={`flex items-center gap-4 p-4 rounded-xl transition-all duration-300 ${state === 'active' ? 'glow-pulse' : ''}`}
                            style={{ background: bgStyle, border: borderStyle }}
                        >
                            {/* Icon */}
                            <div
                                className="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0"
                                style={{ background: iconBg }}
                            >
                                {state === 'active' ? (
                                    <motion.div
                                        animate={{ rotate: 360 }}
                                        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                    >
                                        <Icon className="w-6 h-6" style={{ color: iconColor }} />
                                    </motion.div>
                                ) : state === 'complete' ? (
                                    <CheckCircle className="w-6 h-6" style={{ color: iconColor }} />
                                ) : (
                                    <Icon className="w-6 h-6" style={{ color: iconColor }} />
                                )}
                            </div>

                            {/* Text */}
                            <div className="flex-1">
                                <h3 className={`font-semibold ${state === 'pending' ? 'text-gray-600' : 'text-white'}`}>
                                    {stage.label}
                                </h3>
                                <p className="text-sm text-gray-500">{stage.description}</p>
                            </div>

                            {/* Badge */}
                            {state === 'active' && (
                                <motion.div
                                    className="px-3 py-1 text-xs font-bold rounded-full"
                                    style={{
                                        background: 'rgba(0,229,255,0.15)',
                                        border: '1px solid rgba(0,229,255,0.4)',
                                        color: '#00E5FF',
                                    }}
                                    animate={{ opacity: [1, 0.5, 1] }}
                                    transition={{ duration: 1.5, repeat: Infinity }}
                                >
                                    ACTIVE
                                </motion.div>
                            )}
                            {state === 'complete' && (
                                <div
                                    className="px-3 py-1 text-xs font-bold rounded-full"
                                    style={{
                                        background: 'rgba(204,255,0,0.1)',
                                        border: '1px solid rgba(204,255,0,0.35)',
                                        color: '#CCFF00',
                                    }}
                                >
                                    DONE
                                </div>
                            )}
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
