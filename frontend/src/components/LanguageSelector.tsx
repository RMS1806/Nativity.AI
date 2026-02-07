'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, Check } from 'lucide-react';
import { Language } from '@/types';

interface LanguageSelectorProps {
    languages: Language[];
    selected: string;
    onChange: (code: string) => void;
    disabled?: boolean;
}

export default function LanguageSelector({
    languages,
    selected,
    onChange,
    disabled = false
}: LanguageSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);

    const selectedLanguage = languages.find(l => l.code === selected);

    return (
        <div className="relative">
            <button
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled}
                className={`
          w-full flex items-center justify-between gap-3 px-4 py-3
          bg-white border-2 border-gray-200 rounded-xl
          transition-all duration-200
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-blue-400 cursor-pointer'}
          ${isOpen ? 'border-blue-500 ring-2 ring-blue-100' : ''}
        `}
            >
                <div className="flex items-center gap-3">
                    <span className="text-2xl">{getLanguageFlag(selected)}</span>
                    <div className="text-left">
                        <div className="font-semibold text-gray-800">
                            {selectedLanguage?.name || 'Select Language'}
                        </div>
                        <div className="text-sm text-gray-500">{selectedLanguage?.native}</div>
                    </div>
                </div>
                <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown */}
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    />

                    {/* Options */}
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-xl shadow-xl z-20 overflow-hidden"
                    >
                        {languages.map((language) => (
                            <button
                                key={language.code}
                                onClick={() => {
                                    onChange(language.code);
                                    setIsOpen(false);
                                }}
                                className={`
                  w-full flex items-center gap-3 px-4 py-3 text-left
                  transition-colors duration-150
                  ${language.code === selected
                                        ? 'bg-blue-50 text-blue-700'
                                        : 'hover:bg-gray-50 text-gray-700'
                                    }
                `}
                            >
                                <span className="text-2xl">{getLanguageFlag(language.code)}</span>
                                <div className="flex-1">
                                    <div className="font-medium">{language.name}</div>
                                    <div className="text-sm text-gray-500">{language.native}</div>
                                </div>
                                {language.code === selected && (
                                    <Check className="w-5 h-5 text-blue-600" />
                                )}
                            </button>
                        ))}
                    </motion.div>
                </>
            )}
        </div>
    );
}

function getLanguageFlag(code: string): string {
    const flags: Record<string, string> = {
        hindi: '🇮🇳',
        tamil: '🇮🇳',
        bengali: '🇮🇳',
        telugu: '🇮🇳',
        marathi: '🇮🇳',
    };
    return flags[code] || '🌐';
}
