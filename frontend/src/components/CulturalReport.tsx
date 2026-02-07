'use client';

import {
    X,
    Sparkles,
    Clock,
    MessageSquare,
    ArrowRight,
    Lightbulb,
    Globe,
    AlertCircle
} from 'lucide-react';

// Cultural analysis item from Gemini
export interface CulturalInsight {
    timestamp: string;
    type: 'idiom' | 'metaphor' | 'reference' | 'gesture' | 'sensitivity';
    context: string;
    adaptation: string;
    reasoning: string;
}

// Type icon mapping
const TYPE_ICONS: Record<string, { icon: typeof Sparkles; color: string; bg: string }> = {
    idiom: { icon: MessageSquare, color: 'text-purple-400', bg: 'bg-purple-500/20' },
    metaphor: { icon: Lightbulb, color: 'text-amber-400', bg: 'bg-amber-500/20' },
    reference: { icon: Globe, color: 'text-blue-400', bg: 'bg-blue-500/20' },
    gesture: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-500/20' },
    sensitivity: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
};

function formatType(type: string): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
}

function InsightCard({ insight, index }: { insight: CulturalInsight; index: number }) {
    const typeConfig = TYPE_ICONS[insight.type] || TYPE_ICONS.idiom;
    const Icon = typeConfig.icon;

    return (
        <div className="bg-slate-700/50 rounded-lg p-5">
            {/* Header */}
            <div className="flex items-start gap-3 mb-4">
                <div className={`w-10 h-10 rounded-lg ${typeConfig.bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-5 h-5 ${typeConfig.color}`} />
                </div>
                <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${typeConfig.bg} ${typeConfig.color}`}>
                        {formatType(insight.type)}
                    </span>
                    <span className="text-xs text-slate-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {insight.timestamp}
                    </span>
                </div>
            </div>

            {/* Context */}
            <div className="mb-3">
                <p className="text-sm text-slate-400 mb-1">Original</p>
                <p className="text-white">&quot;{insight.context}&quot;</p>
            </div>

            {/* Arrow */}
            <div className="flex justify-center my-3">
                <div className="flex items-center gap-2 px-3 py-1 bg-blue-500/20 rounded-full">
                    <Sparkles className="w-3.5 h-3.5 text-blue-400" />
                    <span className="text-xs font-medium text-blue-300">Gemini Adapted</span>
                    <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
                </div>
            </div>

            {/* Adaptation */}
            <div className="mb-3">
                <p className="text-sm text-slate-400 mb-1">Adapted</p>
                <p className="text-white text-lg">&quot;{insight.adaptation}&quot;</p>
            </div>

            {/* Reasoning */}
            <div className="mt-4 pt-4 border-t border-slate-600">
                <div className="flex items-start gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-slate-400 italic">{insight.reasoning}</p>
                </div>
            </div>
        </div>
    );
}

function EmptyInsights() {
    return (
        <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-700 flex items-center justify-center">
                <Sparkles className="w-8 h-8 text-slate-500" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No Cultural Adaptations</h3>
            <p className="text-slate-400 text-sm">
                This video didn&apos;t require any significant cultural adaptations.
            </p>
        </div>
    );
}

interface CulturalReportProps {
    insights: CulturalInsight[];
    language?: string;
}

export function CulturalReport({ insights, language }: CulturalReportProps) {
    if (!insights || insights.length === 0) {
        return <EmptyInsights />;
    }

    return (
        <div className="space-y-4">
            {/* Stats */}
            <div className="flex items-center justify-center gap-4 mb-6">
                <div className="text-center px-4 py-2 bg-blue-500/20 rounded-lg">
                    <p className="text-2xl font-bold text-blue-400">{insights.length}</p>
                    <p className="text-xs text-slate-400">Adaptations Made</p>
                </div>
                {language && (
                    <div className="text-center px-4 py-2 bg-purple-500/20 rounded-lg">
                        <p className="text-lg font-bold text-purple-400">{language}</p>
                        <p className="text-xs text-slate-400">Target Language</p>
                    </div>
                )}
            </div>

            {/* Insights list */}
            <div className="space-y-4">
                {insights.map((insight, index) => (
                    <InsightCard key={index} insight={insight} index={index} />
                ))}
            </div>
        </div>
    );
}

interface CulturalReportModalProps {
    isOpen: boolean;
    onClose: () => void;
    insights: CulturalInsight[];
    language?: string;
}

export function CulturalReportModal({ isOpen, onClose, insights, language }: CulturalReportModalProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div
                className="bg-slate-800 border border-slate-700 rounded-xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-5 border-b border-slate-700">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                            <Sparkles className="w-5 h-5 text-purple-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white">Cultural Vibe Check</h2>
                            <p className="text-sm text-slate-400">AI-powered cultural adaptations</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 overflow-y-auto max-h-[65vh]">
                    <CulturalReport insights={insights} language={language} />
                </div>
            </div>
        </div>
    );
}

export default CulturalReport;
