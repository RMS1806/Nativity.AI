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
                className="inline-block w-16 h-7 rounded animate-pulse"
                style={{ background: 'rgba(255,255,255,0.08)' }}
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
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
    loading: boolean;
    index: number;
    isWords?: boolean;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.03, y: -3 }}
            className="rounded-xl p-6 transition-all"
            style={{
                background: 'rgba(255,255,255,0.04)',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                border: '1px solid rgba(255,255,255,0.08)',
            }}
        >
            <div className="flex items-center gap-4">
                <div
                    className="p-3 rounded-xl"
                    style={{ background: 'rgba(255,255,255,0.06)' }}
                >
                    {icon}
                </div>
                <div>
                    <p className="text-sm text-gray-500 font-medium">{label}</p>
                    <p
                        className="text-2xl font-bold"
                        style={{ color: isWords ? '#00E5FF' : 'white' }}
                    >
                        {isWords ? (
                            <AnimatedNumber value={value} isLoading={loading} />
                        ) : loading ? (
                            <span
                                className="inline-block w-10 h-7 rounded animate-pulse"
                                style={{ background: 'rgba(255,255,255,0.08)' }}
                            />
                        ) : (
                            value
                        )}
                    </p>
                </div>
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
        <main className="min-h-screen flex flex-col">
            {/* ── Floating Glass Navbar ─────────────────────────── */}
            <div className="sticky top-0 z-50 pt-4 px-4 pointer-events-none">
                <nav
                    className="max-w-5xl mx-auto flex items-center justify-between px-6 py-3 rounded-full pointer-events-auto"
                    style={{
                        background: 'rgba(255,255,255,0.05)',
                        backdropFilter: 'blur(16px)',
                        WebkitBackdropFilter: 'blur(16px)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
                    }}
                >
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2 group">
                        <motion.div
                            whileHover={{ rotate: 180, scale: 1.1 }}
                            transition={{ duration: 0.3 }}
                            className="w-9 h-9 rounded-xl flex items-center justify-center"
                            style={{ background: 'linear-gradient(135deg, #00E5FF, #FF00FF)' }}
                        >
                            <Zap className="w-4 h-4 text-black" />
                        </motion.div>
                        <span className="text-xl font-bold neon-text-gradient">
                            Nativity.ai
                        </span>
                    </Link>

                    {/* Nav links */}
                    <nav className="hidden md:flex items-center gap-2">
                        <Link href="/">
                            <motion.div
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white rounded-full transition-all"
                                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid transparent' }}
                            >
                                <Home className="w-4 h-4" />
                                Home
                            </motion.div>
                        </Link>
                        <div
                            className="flex items-center gap-2 px-4 py-2 text-sm text-white rounded-full"
                            style={{
                                background: 'rgba(0,229,255,0.08)',
                                border: '1px solid rgba(0,229,255,0.25)',
                            }}
                        >
                            <LayoutDashboard className="w-4 h-4" style={{ color: '#00E5FF' }} />
                            Dashboard
                        </div>
                    </nav>

                    <UserButton afterSignOutUrl="/" />
                </nav>
            </div>

            {/* ── Main Content ──────────────────────────────────── */}
            <div className="flex-1 max-w-6xl mx-auto w-full px-6 py-10">
                {/* Welcome */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h2 className="text-2xl font-bold text-white mb-1">
                        Welcome back{isLoaded && user?.firstName ? `, ${user.firstName}` : ''}!{' '}
                        <span className="neon-text-gradient">👋</span>
                    </h2>
                    <p className="text-gray-500">Your localization command center</p>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <StatCard
                        icon={<FolderOpen className="w-5 h-5" style={{ color: '#FF00FF' }} />}
                        label="Total Projects"
                        value={stats.total_projects}
                        loading={loading}
                        index={0}
                    />
                    <StatCard
                        icon={<Globe className="w-5 h-5" style={{ color: '#FF00FF' }} />}
                        label="Languages Used"
                        value={stats.languages_used}
                        loading={loading}
                        index={1}
                    />
                    <StatCard
                        icon={<BookOpen className="w-5 h-5" style={{ color: '#00E5FF' }} />}
                        label="Words Localized"
                        value={stats.words_localized}
                        loading={loading}
                        index={2}
                        isWords={true}
                    />
                </div>

                {/* History Table */}
                <div
                    className="rounded-2xl p-6"
                    style={{
                        background: 'rgba(255,255,255,0.03)',
                        backdropFilter: 'blur(12px)',
                        WebkitBackdropFilter: 'blur(12px)',
                        border: '1px solid rgba(255,255,255,0.08)',
                    }}
                >
                    <HistoryTable />
                </div>
            </div>

            {/* FAB */}
            <Link href="/">
                <motion.div
                    whileHover={{ scale: 1.1, boxShadow: '0 0 40px rgba(255,0,255,0.5)' }}
                    whileTap={{ scale: 0.95 }}
                    className="fixed bottom-6 right-6 w-14 h-14 rounded-full flex items-center justify-center shadow-2xl cursor-pointer"
                    style={{
                        background: 'linear-gradient(135deg, #00E5FF, #FF00FF)',
                        boxShadow: '0 0 20px rgba(0,229,255,0.3)',
                    }}
                >
                    <Plus className="w-6 h-6 text-black" />
                </motion.div>
            </Link>

            {/* Footer */}
            <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }} className="mt-20">
                <div className="max-w-6xl mx-auto px-6 py-8 text-center">
                    <p className="text-sm text-gray-600">
                        Nativity<span style={{ color: '#00E5FF' }}>.</span>ai © 2024 • Hyper-localizing the Internet for Bharat
                    </p>
                </div>
            </footer>
        </main>
    );
}
