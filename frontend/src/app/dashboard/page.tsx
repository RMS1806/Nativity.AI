'use client';

import { useState, useEffect, useRef } from 'react';
import { useUser, UserButton } from '@clerk/nextjs';
import { motion, useMotionValue, useTransform, animate } from 'framer-motion';
import { Plus, Zap, Home, LayoutDashboard, Globe, BookOpen, FolderOpen } from 'lucide-react';
import Link from 'next/link';
import HistoryTable from '@/components/HistoryTable';
import { useHistory, DashboardStats } from '@/lib/auth-api';

// ─── Animated Counter ─────────────────────────────────────────────────
function AnimatedNumber({ value, isLoading }: { value: number; isLoading: boolean }) {
    const motionVal = useMotionValue(0);
    const [displayVal, setDisplayVal] = useState(0);

    useEffect(() => {
        if (isLoading || value === 0) return;
        const controls = animate(motionVal, value, {
            duration: 1.8,
            ease: 'easeOut',
            onUpdate: (v) => setDisplayVal(Math.round(v)),
        });
        return controls.stop;
    }, [value, isLoading, motionVal]);

    if (isLoading) {
        return (
            <span
                className="inline-block w-16 h-8 animate-pulse neo-border"
                style={{ backgroundColor: '#eee7df' }}
            />
        );
    }

    return <>{displayVal.toLocaleString()}</>;
}

// ─── Stat Card ────────────────────────────────────────────────────────
function StatCard({
    icon,
    label,
    value,
    loading,
    index,
    isWords = false,
    bgColor = '#FFFFFF',
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    loading: boolean;
    index: number;
    isWords?: boolean;
    bgColor?: string;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ y: -4, x: -2 }}
            className="neo-border neo-shadow p-6 flex flex-col justify-center transition-all"
            style={{ backgroundColor: bgColor }}
        >
            <span className="font-mono-label text-[#5c403d] uppercase mb-2 tracking-wider text-xs">
                {label}
            </span>
            <div className="flex items-center gap-4">
                <div className="p-3 neo-border" style={{ backgroundColor: '#f4ede5' }}>
                    {icon}
                </div>
                <span className="font-headline text-4xl font-bold text-[#1A1A1A]">
                    {isWords ? (
                        <AnimatedNumber value={value} isLoading={loading} />
                    ) : loading ? (
                        <span
                            className="inline-block w-10 h-8 animate-pulse neo-border"
                            style={{ backgroundColor: '#eee7df' }}
                        />
                    ) : (
                        value
                    )}
                </span>
            </div>
        </motion.div>
    );
}

export default function DashboardPage() {
    const { user, isLoaded } = useUser();
    const { data, loading } = useHistory();

    const stats: DashboardStats = data?.stats || {
        total_projects: 0,
        languages_used: 0,
        words_localized: 0,
    };

    return (
        <main className="min-h-screen flex flex-col md:flex-row">
            {/* ── Side Nav (Desktop) ─────────────────────────── */}
            <aside
                className="hidden lg:flex flex-col fixed left-0 top-0 h-full w-64 bg-white z-40 p-2"
                style={{ borderRight: '3px solid #1A1A1A' }}
            >
                <div className="mb-6 mt-2 px-4">
                    <h1 className="text-xl font-bold font-headline text-[#1A1A1A]">Creator Studio</h1>
                    <p className="font-mono-label text-[#5c403d] mt-1">Localization Hub</p>
                </div>
                <nav className="flex-1 space-y-2">
                    <Link
                        href="/"
                        className="flex items-center gap-3 px-4 py-3 font-mono-label text-[#1A1A1A] hover:bg-[#eee7df] hover:translate-x-1 transition-all"
                    >
                        <Home className="w-5 h-5" />
                        Home
                    </Link>
                    <div
                        className="flex items-center gap-3 px-4 py-3 font-mono-label text-white neo-border"
                        style={{
                            backgroundColor: '#9c48ea',
                            boxShadow: '4px 4px 0px 0px #1A1A1A',
                        }}
                    >
                        <LayoutDashboard className="w-5 h-5" />
                        Dashboard
                    </div>
                </nav>
                <div className="mt-auto space-y-2 pt-4" style={{ borderTop: '3px solid #1A1A1A' }}>
                    <Link href="/">
                        <motion.button
                            whileHover={{ y: -2, x: -2 }}
                            whileTap={{ y: 2, x: 2 }}
                            className="w-full flex justify-center items-center gap-2 py-3 bg-[#ba061b] text-white font-mono-label neo-border neo-shadow transition-all"
                        >
                            <Plus className="w-5 h-5" />
                            New Project
                        </motion.button>
                    </Link>
                    <UserButton afterSignOutUrl="/" />
                </div>
            </aside>

            {/* ── Mobile TopNav ─────────────────────────────── */}
            <nav
                className="lg:hidden flex justify-between items-center px-4 h-20 bg-white sticky top-0 z-50"
                style={{ borderBottom: '3px solid #1A1A1A' }}
            >
                <div className="text-xl font-bold font-headline text-[#1A1A1A]">
                    Nativity.ai
                </div>
                <div className="flex items-center gap-3">
                    <Link href="/">
                        <motion.div
                            whileHover={{ y: -2 }}
                            className="flex items-center gap-2 px-3 py-2 font-mono-label text-[#1A1A1A] neo-border bg-white"
                            style={{ boxShadow: '2px 2px 0px 0px #1A1A1A' }}
                        >
                            <Home className="w-4 h-4" />
                        </motion.div>
                    </Link>
                    <UserButton afterSignOutUrl="/" />
                </div>
            </nav>

            {/* ── Main Content ──────────────────────────────── */}
            <div className="flex-1 lg:ml-64 p-4 md:p-10 min-h-screen">
                {/* Welcome */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h2 className="text-3xl font-bold text-[#1A1A1A] mb-1 font-headline tracking-tight">
                        Welcome back{isLoaded && user?.firstName ? `, ${user.firstName}` : ''}! 👋
                    </h2>
                    <p className="text-[#5c403d]">Your localization command center</p>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                    <StatCard
                        icon={<FolderOpen className="w-5 h-5 text-[#ba061b]" />}
                        label="Total Projects"
                        value={stats.total_projects}
                        loading={loading}
                        index={0}
                        bgColor="#FFFFFF"
                    />
                    <StatCard
                        icon={<Globe className="w-5 h-5 text-[#8127cf]" />}
                        label="Languages Used"
                        value={stats.languages_used}
                        loading={loading}
                        index={1}
                        bgColor="#F3EDFF"
                    />
                    <StatCard
                        icon={<BookOpen className="w-5 h-5 text-[#0058be]" />}
                        label="Words Localized"
                        value={stats.words_localized}
                        loading={loading}
                        index={2}
                        isWords={true}
                        bgColor="#FFFFFF"
                    />
                </div>

                {/* History Table */}
                <div
                    className="neo-border neo-shadow p-6 bg-white"
                    style={{ borderRadius: '0.5rem' }}
                >
                    <HistoryTable />
                </div>
            </div>

            {/* FAB */}
            <Link href="/">
                <motion.div
                    whileHover={{ y: -4, x: -4 }}
                    whileTap={{ y: 4, x: 4 }}
                    className="fixed bottom-6 right-6 w-16 h-16 flex items-center justify-center cursor-pointer"
                    style={{
                        backgroundColor: '#8127cf',
                        border: '4px solid #1A1A1A',
                        borderRadius: '9999px',
                        boxShadow: '4px 4px 0px 0px #1A1A1A',
                        transition: 'all 0.2s ease',
                    }}
                >
                    <Plus className="w-6 h-6 text-white" />
                </motion.div>
            </Link>
        </main>
    );
}
