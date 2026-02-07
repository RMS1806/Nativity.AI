'use client';

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

interface ResultCardProps {
    job: LocalizationJob;
}

export default function ResultCard({ job }: ResultCardProps) {
    const results = job.results;
    const culturalReport = results?.cultural_report;

    return (
        <div className="w-full max-w-4xl mx-auto space-y-6">
            {/* Success Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center"
            >
                <motion.div
                    className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-400 to-emerald-500 flex items-center justify-center"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
                >
                    <CheckCircle2 className="w-10 h-10 text-white" />
                </motion.div>
                <h2 className="text-3xl font-bold text-gray-800">
                    🎉 Localization Complete!
                </h2>
                <p className="text-gray-600 mt-2">
                    Your video is now available in <span className="font-semibold text-blue-600 capitalize">{job.target_language}</span>
                </p>
            </motion.div>

            {/* Video Player */}
            {results?.output_url && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="rounded-2xl overflow-hidden shadow-xl bg-black"
                >
                    <video
                        src={results.output_url}
                        controls
                        className="w-full aspect-video"
                        poster="/video-poster.jpg"
                    >
                        Your browser does not support the video tag.
                    </video>
                </motion.div>
            )}

            {/* Action Buttons */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="grid grid-cols-1 sm:grid-cols-2 gap-4"
            >
                {/* Download Full Version */}
                {results?.output_url && (
                    <a
                        href={results.output_url}
                        download
                        className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-[1.02]"
                    >
                        <Download className="w-5 h-5" />
                        Download Full Video
                        {results.file_size_mb && (
                            <span className="text-sm opacity-75">({results.file_size_mb.toFixed(1)} MB)</span>
                        )}
                    </a>
                )}

                {/* Download WhatsApp Version */}
                {results?.whatsapp_url && (
                    <a
                        href={results.whatsapp_url}
                        download
                        className="flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-green-500 to-emerald-600 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 hover:scale-[1.02]"
                    >
                        <Smartphone className="w-5 h-5" />
                        WhatsApp Version
                        <span className="text-sm opacity-75">(&lt;15 MB)</span>
                    </a>
                )}
            </motion.div>

            {/* Cultural Report Card */}
            {culturalReport && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 }}
                    className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-6 border border-purple-200"
                >
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h3 className="font-bold text-gray-800">Cultural Adaptation Report</h3>
                            <p className="text-sm text-gray-600">Powered by Gemini AI</p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
                        {/* Quality Score */}
                        <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                            <div className="text-3xl font-bold text-purple-600">
                                {culturalReport.localization_quality_score}/10
                            </div>
                            <div className="text-xs text-gray-500 mt-1">Quality Score</div>
                        </div>

                        {/* Idioms Adapted */}
                        <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                            <div className="text-3xl font-bold text-blue-600">
                                {culturalReport.idioms_adapted}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">Idioms Adapted</div>
                        </div>

                        {/* Cultural Notes */}
                        <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                            <div className="text-3xl font-bold text-green-600">
                                {culturalReport.cultural_sensitivities?.length || 0}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">Cultural Notes</div>
                        </div>

                        {/* Language */}
                        <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                            <Globe className="w-8 h-8 text-indigo-600 mx-auto" />
                            <div className="text-xs text-gray-500 mt-2 capitalize">{job.target_language}</div>
                        </div>
                    </div>

                    {/* Cultural Notes */}
                    {culturalReport.notes && (
                        <div className="bg-white rounded-xl p-4 shadow-sm">
                            <div className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                                <MessageSquare className="w-4 h-4" />
                                Gemini's Notes
                            </div>
                            <p className="text-gray-600 text-sm">{culturalReport.notes}</p>
                        </div>
                    )}

                    {/* Cultural Sensitivities */}
                    {culturalReport.cultural_sensitivities && culturalReport.cultural_sensitivities.length > 0 && (
                        <div className="mt-4 space-y-2">
                            <h4 className="text-sm font-medium text-gray-700">Cultural Observations</h4>
                            {culturalReport.cultural_sensitivities.map((item, index) => (
                                <div key={index} className="bg-white rounded-lg p-3 text-sm shadow-sm">
                                    <div className="flex justify-between">
                                        <span className="font-medium text-gray-800">{item.description}</span>
                                        <span className="text-xs text-gray-400">{item.timestamp}</span>
                                    </div>
                                    <p className="text-gray-600 mt-1">{item.recommendation}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </motion.div>
            )}

            {/* Share Section */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.6 }}
                className="text-center pt-4"
            >
                <button className="inline-flex items-center gap-2 text-gray-500 hover:text-blue-600 transition-colors">
                    <Share2 className="w-4 h-4" />
                    <span className="text-sm">Share your localized content</span>
                </button>
            </motion.div>
        </div>
    );
}
