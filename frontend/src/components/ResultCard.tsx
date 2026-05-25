'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
    Download,
    MessageSquare,
    Sparkles,
    Play,
    CheckCircle2,
    Globe,
    Smartphone,
    Share2
} from 'lucide-react';
import { LocalizationJob, CulturalReport } from '@/types';
import { CulturalReportModal } from './CulturalReport';
import { downloadSrt } from '@/lib/srt-utils';

interface ResultCardProps {
    job: LocalizationJob;
}

export default function ResultCard({ job }: ResultCardProps) {
    const results = job.results;
    const culturalReport = results?.cultural_report;
    const [isReportOpen, setIsReportOpen] = useState(false);

    const handleDownloadSubtitles = () => {
        if (results?.analysis?.segments) {
            downloadSrt(results.analysis.segments, job.input_file.split('/').pop() || 'Video');
        } else {
            alert('Subtitles are not available for this video.');
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto">
            {/* Main Success Card */}
            <div className="bg-white neo-border neo-shadow-lg p-6 md:p-10 flex flex-col gap-8">
                {/* Success Header */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="text-center space-y-4"
                >
                    <motion.div
                        className="inline-flex items-center justify-center w-20 h-20 neo-border neo-shadow"
                        style={{ backgroundColor: '#BFFF00', borderRadius: '9999px' }}
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
                    >
                        <CheckCircle2 className="w-10 h-10 text-[#1A1A1A]" />
                    </motion.div>
                    <h2 className="text-3xl md:text-5xl font-bold text-[#1A1A1A] font-headline">
                        Localization Complete!
                    </h2>
                    <p className="text-lg text-[#5c403d] max-w-2xl mx-auto">
                        Your video is now available in{' '}
                        <span className="font-bold text-[#8127cf] capitalize">{job.target_language}</span>
                    </p>
                </motion.div>

                {/* Video Player */}
                {results?.output_url && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        className="relative w-full aspect-video neo-border neo-shadow overflow-hidden"
                        style={{ backgroundColor: '#1A1A1A' }}
                    >
                        <video
                            src={results.output_url}
                            controls
                            className="w-full h-full"
                            poster="/video-poster.jpg"
                        >
                            Your browser does not support the video tag.
                        </video>
                        {/* Language badge overlay */}
                        <div
                            className="absolute top-4 right-4 bg-white neo-border neo-shadow px-4 py-2 flex gap-2 z-10 pointer-events-none"
                        >
                            <span className="font-mono-label font-bold capitalize">{job.target_language}</span>
                        </div>
                    </motion.div>
                )}

                {/* Action Buttons */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-4"
                >
                    {/* Download Full Version */}
                    {results?.output_url && (
                        <a
                            href={results.output_url}
                            download
                            className="flex items-center justify-center gap-2 py-4 px-6 font-mono-label font-bold uppercase tracking-wider neo-border neo-shadow neo-shadow-hover neo-shadow-active transition-all duration-200 text-white"
                            style={{ backgroundColor: '#0058be' }}
                        >
                            <Download className="w-5 h-5" />
                            Download Full
                            {results.file_size_mb && (
                                <span className="text-xs opacity-75">({results.file_size_mb.toFixed(1)} MB)</span>
                            )}
                        </a>
                    )}

                    {/* Download WhatsApp Version */}
                    {results?.whatsapp_url && (
                        <a
                            href={results.whatsapp_url}
                            download
                            className="flex items-center justify-center gap-2 py-4 px-6 font-mono-label font-bold uppercase tracking-wider neo-border neo-shadow neo-shadow-hover neo-shadow-active transition-all duration-200 text-[#1A1A1A]"
                            style={{ backgroundColor: '#BFFF00' }}
                        >
                            <Share2 className="w-5 h-5" />
                            WhatsApp Version
                        </a>
                    )}

                    {/* Subtitles */}
                    <button
                        onClick={handleDownloadSubtitles}
                        className="flex items-center justify-center gap-2 py-4 px-6 font-mono-label font-bold uppercase tracking-wider neo-border neo-shadow neo-shadow-hover neo-shadow-active transition-all duration-200 bg-white text-[#1A1A1A]"
                    >
                        <MessageSquare className="w-5 h-5" />
                        Download Subtitles
                    </button>
                </motion.div>

                {/* Cultural Report Card */}
                {culturalReport && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="neo-border neo-shadow p-6 flex flex-col sm:flex-row items-center justify-between gap-4"
                        style={{ backgroundColor: '#F3EDFF' }}
                    >
                        <div className="flex items-center gap-4">
                            <div
                                className="w-12 h-12 neo-border neo-shadow flex items-center justify-center"
                                style={{ backgroundColor: '#9c48ea' }}
                            >
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h3 className="font-headline text-xl font-bold text-[#1A1A1A]">Cultural Insights Generated</h3>
                                <p className="text-sm text-[#5c403d]">
                                    Quality Score: <span className="font-bold text-[#8127cf]">{culturalReport.localization_quality_score}/10</span>
                                    {' '} • {culturalReport.idioms_adapted} idioms adapted
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsReportOpen(true)}
                            className="inline-block bg-[#ba061b] text-white neo-border py-3 px-6 font-mono-label font-bold uppercase tracking-wider neo-shadow neo-shadow-hover neo-shadow-active transition-all duration-200 whitespace-nowrap"
                        >
                            View Report
                        </button>
                    </motion.div>
                )}

                {/* Cultural Notes (if no report card, show raw notes) */}
                {culturalReport?.notes && !culturalReport.localization_quality_score && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="neo-border neo-shadow p-6 bg-white"
                    >
                        <div className="flex items-center gap-2 font-mono-label text-[#5c403d] mb-3 uppercase tracking-wider text-xs">
                            <MessageSquare className="w-4 h-4" />
                            Gemini's Notes
                        </div>
                        <p className="text-[#1A1A1A]">{culturalReport.notes}</p>
                    </motion.div>
                )}

                {/* Cultural Sensitivities */}
                {culturalReport?.cultural_sensitivities && culturalReport.cultural_sensitivities.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        className="space-y-3"
                    >
                        <h4 className="font-mono-label text-[#5c403d] uppercase tracking-wider text-xs">Cultural Observations</h4>
                        {culturalReport.cultural_sensitivities.map((item, index) => (
                            <div key={index} className="neo-border p-4 bg-white" style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}>
                                <div className="flex justify-between">
                                    <span className="font-bold text-[#1A1A1A]">{item.description}</span>
                                    <span className="font-mono-label text-xs text-[#906f6c]">{item.timestamp}</span>
                                </div>
                                <p className="text-sm text-[#5c403d] mt-1">{item.recommendation}</p>
                            </div>
                        ))}
                    </motion.div>
                )}

                {/* Start Another */}
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.7 }}
                    className="text-center"
                >
                    <button
                        onClick={() => window.location.reload()}
                        className="font-mono-label text-[#5c403d] hover:text-[#1A1A1A] underline decoration-[#1A1A1A]/30 hover:decoration-[#1A1A1A] decoration-2 underline-offset-4 transition-all duration-200"
                    >
                        Start Another Localization
                    </button>
                </motion.div>
            </div>

            {/* Cultural Report Modal */}
            <CulturalReportModal
                isOpen={isReportOpen}
                onClose={() => setIsReportOpen(false)}
                insights={(results?.analysis as any)?.cultural_analysis || []}
                language={job.target_language}
            />
        </div>
    );
}
