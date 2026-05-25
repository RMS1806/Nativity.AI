'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';
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
    return (
        <div className="flex flex-wrap gap-4 justify-center">
            {languages.map((language) => {
                const isSelected = language.code === selected;
                return (
                    <motion.button
                        key={language.code}
                        onClick={() => !disabled && onChange(language.code)}
                        disabled={disabled}
                        whileHover={!disabled ? { y: -4 } : {}}
                        whileTap={!disabled ? { y: 2, x: 2 } : {}}
                        className={`
                            px-6 py-2 font-mono-label neo-border transition-all duration-200
                            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                            ${isSelected
                                ? 'bg-[#8127cf] text-white -translate-y-1'
                                : 'bg-[#f4ede5] text-[#1A1A1A] hover:bg-[#eee7df]'
                            }
                        `}
                        style={{
                            borderRadius: '9999px',
                            boxShadow: isSelected ? '4px 4px 0px 0px #1A1A1A' : 'none',
                        }}
                    >
                        <span className="flex items-center gap-2">
                            {isSelected && <Check className="w-4 h-4" />}
                            {language.name}
                            {language.native && (
                                <span className="text-xs opacity-75">{language.native}</span>
                            )}
                        </span>
                    </motion.button>
                );
            })}
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
