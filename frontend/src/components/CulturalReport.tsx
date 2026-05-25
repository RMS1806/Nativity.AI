'use client';

import {
    X,
    Sparkles,
    MessageSquare,
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
    idiom: { icon: MessageSquare, color: 'text-[#8127cf]', bg: 'bg-[#F3EDFF]' },
    metaphor: { icon: Lightbulb, color: 'text-[#FBBF24]', bg: 'bg-[#fff8f1]' },
    reference: { icon: Globe, color: 'text-[#0058be]', bg: 'bg-[#d8e2ff]' },
    gesture: { icon: AlertCircle, color: 'text-[#FF2D78]', bg: 'bg-[#ffdad7]' },
    sensitivity: { icon: AlertCircle, color: 'text-[#ba061b]', bg: 'bg-[#ffdad7]' },
};

function formatType(type: string): string {
    return type.charAt(0).toUpperCase() + type.slice(1);
}

function InsightCard({ insight, index }: { insight: CulturalInsight; index: number }) {
    const typeConfig = TYPE_ICONS[insight.type] || TYPE_ICONS.idiom;
    const Icon = typeConfig.icon;

    return (
        <div className="bg-white neo-border p-5" style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}>
            {/* Header */}
            <div className="flex items-start justify-between mb-4 pb-4" style={{ borderBottom: '3px solid #1A1A1A' }}>
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 neo-border flex items-center justify-center flex-shrink-0 ${typeConfig.bg}`}>
                        <Icon className={`w-5 h-5 ${typeConfig.color}`} />
                    </div>
                    <span className={`px-2 py-0.5 font-mono-label font-bold uppercase neo-border ${typeConfig.bg} ${typeConfig.color}`}>
                        {formatType(insight.type)}
                    </span>
                </div>
                <span className="font-mono-label text-sm text-[#5c403d] font-bold">
                    {insight.timestamp}
                </span>
            </div>

            {/* Context -> Adaptation */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <div className="bg-[#f4ede5] p-3 neo-border">
                    <p className="font-mono-label text-xs uppercase tracking-wider text-[#5c403d] mb-1">Original Context</p>
                    <p className="text-[#1A1A1A] font-bold">"{insight.context}"</p>
                </div>
                <div className="bg-[#BFFF00] p-3 neo-border" style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}>
                    <p className="font-mono-label text-xs uppercase tracking-wider text-[#1A1A1A] mb-1">Adapted</p>
                    <p className="text-[#1A1A1A] font-bold text-lg">"{insight.adaptation}"</p>
                </div>
            </div>

            {/* Reasoning */}
            <div className="bg-[#F3EDFF] p-3 neo-border mt-2">
                <div className="flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-[#8127cf] flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-[#5c403d] font-mono-label">{insight.reasoning}</p>
                </div>
            </div>
        </div>
    );
}

function EmptyInsights() {
    return (
        <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 neo-border flex items-center justify-center bg-[#f4ede5]">
                <Sparkles className="w-8 h-8 text-[#5c403d]" />
            </div>
            <h3 className="text-xl font-bold font-headline text-[#1A1A1A] mb-2">No Cultural Adaptations</h3>
            <p className="text-[#5c403d] font-mono-label">
                This video didn't require any significant cultural adaptations.
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
        <div className="space-y-6">
            {/* Stats */}
            <div className="flex items-center justify-center gap-4 mb-6">
                <div className="text-center px-6 py-4 bg-[#BFFF00] neo-border" style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}>
                    <p className="text-3xl font-headline font-bold text-[#1A1A1A]">{insights.length}</p>
                    <p className="text-xs font-mono-label uppercase tracking-wider text-[#1A1A1A] mt-1">Adaptations</p>
                </div>
                {language && (
                    <div className="text-center px-6 py-4 bg-[#8127cf] neo-border" style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}>
                        <p className="text-2xl font-headline font-bold text-white uppercase">{language}</p>
                        <p className="text-xs font-mono-label uppercase tracking-wider text-white mt-2">Target</p>
                    </div>
                )}
            </div>

            {/* Insights list */}
            <div className="space-y-6">
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(0,0,0,0.6)' }} onClick={onClose}>
            <div
                className="bg-[#fff8f1] neo-border neo-shadow-lg max-w-2xl w-full max-h-[85vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-5 bg-white" style={{ borderBottom: '3px solid #1A1A1A' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 neo-border flex items-center justify-center bg-[#F3EDFF]" style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}>
                            <Sparkles className="w-6 h-6 text-[#8127cf]" />
                        </div>
                        <div>
                            <h2 className="text-xl font-headline font-bold text-[#1A1A1A]">Cultural Insights</h2>
                            <p className="text-sm font-mono-label text-[#5c403d] uppercase tracking-wider">Powered by Gemini AI</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-[#1A1A1A] bg-white neo-border hover:bg-[#eee7df] transition-colors"
                        style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[65vh]">
                    <CulturalReport insights={insights} language={language} />
                </div>
            </div>
        </div>
    );
}

export default CulturalReport;
