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
        label: 'Analyzing Audio',
        description: 'Sending video to cloud',
        icon: CloudUpload,
        statuses: ['uploading'],
    },
    {
        id: 'analyzing',
        label: 'Cultural Adaptation',
        description: 'Understanding context & culture',
        icon: Brain,
        statuses: ['analyzing'],
    },
    {
        id: 'generating_audio',
        label: 'Audio Generation',
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
        <div className="w-full max-w-3xl mx-auto py-8">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Left: Upload Progress */}
                <div className="lg:col-span-5">
                    <div className="bg-white neo-border neo-shadow p-6" style={{ borderRadius: '0.5rem' }}>
                        <div className="flex justify-between items-end mb-4">
                            <h4 className="font-mono-label text-[#5c403d] uppercase tracking-wider">Processing</h4>
                            <span className="font-headline text-2xl font-bold text-[#ba061b]">{progress}%</span>
                        </div>
                        {/* Progress Bar */}
                        <div
                            className="h-6 w-full neo-border overflow-hidden"
                            style={{ backgroundColor: '#eee7df', borderRadius: '9999px' }}
                        >
                            <motion.div
                                className="h-full"
                                style={{
                                    backgroundColor: '#FBBF24',
                                    borderRight: progress > 0 && progress < 100 ? '3px solid #1A1A1A' : 'none',
                                }}
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                                transition={{ duration: 0.5 }}
                            />
                        </div>
                        <motion.p
                            key={message}
                            initial={{ opacity: 0, y: -4 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-sm text-[#5c403d] mt-3 text-right font-mono-label"
                        >
                            {message || 'Processing…'}
                        </motion.p>
                    </div>
                </div>

                {/* Right: Processing Checklist */}
                <div className="lg:col-span-7">
                    <div
                        className="neo-border neo-shadow p-6"
                        style={{ backgroundColor: '#F3EDFF', borderRadius: '0.5rem' }}
                    >
                        <h4 className="font-headline text-xl font-bold text-[#1A1A1A] mb-6 flex items-center gap-2">
                            <Zap className="w-5 h-5 text-[#8127cf] animate-neo-spin" />
                            Processing Status
                        </h4>
                        <div className="space-y-4">
                            {stages.map((stage, index) => {
                                const state = getStageState(stage);
                                const Icon = stage.icon;

                                return (
                                    <motion.div
                                        key={stage.id}
                                        initial={{ opacity: 0, x: -20 }}
                                        animate={{ opacity: state === 'pending' ? 0.4 : 1, x: 0 }}
                                        transition={{ delay: index * 0.08 }}
                                        className={`flex items-center gap-4 ${state === 'active'
                                            ? 'p-3 -ml-1 bg-white neo-border'
                                            : 'p-2'
                                            }`}
                                        style={{
                                            borderRadius: state === 'active' ? '0.25rem' : undefined,
                                            boxShadow: state === 'active' ? '2px 2px 0px 0px #1A1A1A' : undefined,
                                        }}
                                    >
                                        {/* Icon */}
                                        <div
                                            className="w-8 h-8 neo-border flex items-center justify-center flex-shrink-0"
                                            style={{
                                                backgroundColor: state === 'complete'
                                                    ? '#BFFF00'
                                                    : state === 'active'
                                                        ? '#FBBF24'
                                                        : '#f4ede5',
                                                borderRadius: '0.25rem',
                                            }}
                                        >
                                            {state === 'complete' ? (
                                                <CheckCircle className="w-4 h-4 text-[#1A1A1A]" />
                                            ) : state === 'active' ? (
                                                <motion.div
                                                    animate={{ scale: [1, 1.2, 1] }}
                                                    transition={{ duration: 1.5, repeat: Infinity }}
                                                >
                                                    <Icon className="w-4 h-4 text-[#1A1A1A]" />
                                                </motion.div>
                                            ) : (
                                                <Icon className="w-4 h-4 text-[#5c403d]" />
                                            )}
                                        </div>

                                        {/* Text */}
                                        <span className={`font-mono-label ${state === 'complete' ? 'line-through opacity-50' : ''
                                            } ${state === 'active' ? 'font-bold text-[#1A1A1A]' : 'text-[#1A1A1A]'
                                            }`}>
                                            {stage.label}
                                        </span>

                                        {/* Active badge */}
                                        {state === 'active' && (
                                            <motion.span
                                                className="ml-auto px-2 py-0.5 neo-border font-mono-label text-xs font-bold uppercase"
                                                style={{ backgroundColor: '#FBBF24' }}
                                                animate={{ opacity: [1, 0.5, 1] }}
                                                transition={{ duration: 1.5, repeat: Infinity }}
                                            >
                                                ACTIVE
                                            </motion.span>
                                        )}
                                    </motion.div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
