'use client';

import { useUser, UserButton } from '@clerk/nextjs';
import { motion } from 'framer-motion';
import { Plus, Zap, Home, LayoutDashboard, Globe, Clock, FolderOpen } from 'lucide-react';
import Link from 'next/link';
import HistoryTable from '@/components/HistoryTable';
import { useHistory, DashboardStats } from '@/lib/auth-api';

// Stat Card - Dark Tech Style
function StatCard({
    icon,
    label,
    value,
    loading,
    index
}: {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    loading: boolean;
    index: number;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ scale: 1.02, borderColor: 'rgba(168, 85, 247, 0.3)' }}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 transition-colors"
        >
            <div className="flex items-center gap-4">
                <div className="p-3 rounded-lg bg-gray-800">
                    {icon}
                </div>
                <div>
                    <p className="text-sm text-gray-500 font-medium">{label}</p>
                    <p className="text-2xl font-bold text-white">
                        {loading ? (
                            <span className="inline-block w-16 h-7 bg-gray-800 rounded animate-pulse" />
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
        minutes_saved: 0
    };

    return (
        <main className="min-h-screen">
            {/* Navbar - Pure Dark */}
            <header className="sticky top-0 z-50 bg-black/95 backdrop-blur-sm border-b border-gray-900">
                <div className="max-w-6xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <Link href="/" className="flex items-center gap-2 group">
                            <motion.div
                                whileHover={{ rotate: 180 }}
                                transition={{ duration: 0.3 }}
                                className="w-9 h-9 rounded-lg bg-gradient-to-r from-fuchsia-600 to-purple-600 flex items-center justify-center"
                            >
                                <Zap className="w-4 h-4 text-white" />
                            </motion.div>
                            <span className="text-xl font-bold text-white">
                                Nativity<span className="text-fuchsia-500">.</span>ai
                            </span>
                        </Link>

                        <nav className="hidden md:flex items-center gap-1">
                            <Link href="/">
                                <motion.div
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-900 rounded-lg transition-all"
                                >
                                    <Home className="w-4 h-4" />
                                    Home
                                </motion.div>
                            </Link>
                            <div className="flex items-center gap-2 px-4 py-2 text-sm text-white bg-gray-900 border border-gray-800 rounded-lg">
                                <LayoutDashboard className="w-4 h-4 text-fuchsia-500" />
                                Dashboard
                            </div>
                        </nav>

                        <UserButton afterSignOutUrl="/" />
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <div className="max-w-6xl mx-auto px-6 py-10">
                {/* Welcome */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <h2 className="text-2xl font-bold text-white mb-1">
                        Welcome back{isLoaded && user?.firstName ? `, ${user.firstName}` : ''}! 👋
                    </h2>
                    <p className="text-gray-500">Your localization command center</p>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                    <StatCard
                        icon={<FolderOpen className="w-5 h-5 text-fuchsia-500" />}
                        label="Total Projects"
                        value={stats.total_projects}
                        loading={loading}
                        index={0}
                    />
                    <StatCard
                        icon={<Globe className="w-5 h-5 text-purple-500" />}
                        label="Languages Used"
                        value={stats.languages_used}
                        loading={loading}
                        index={1}
                    />
                    <StatCard
                        icon={<Clock className="w-5 h-5 text-violet-500" />}
                        label="Time Saved"
                        value={`${stats.minutes_saved} mins`}
                        loading={loading}
                        index={2}
                    />
                </div>

                {/* History Table */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="bg-gray-900 border border-gray-800 rounded-xl p-6"
                >
                    <HistoryTable />
                </motion.div>
            </div>

            {/* FAB */}
            <Link href="/">
                <motion.div
                    whileHover={{ scale: 1.1, boxShadow: '0 0 30px rgba(168, 85, 247, 0.4)' }}
                    whileTap={{ scale: 0.95 }}
                    className="fixed bottom-6 right-6 w-14 h-14 bg-gradient-to-r from-fuchsia-600 to-purple-600 rounded-full flex items-center justify-center shadow-lg cursor-pointer"
                >
                    <Plus className="w-6 h-6 text-white" />
                </motion.div>
            </Link>

            {/* Footer */}
            <footer className="border-t border-gray-900 mt-20">
                <div className="max-w-6xl mx-auto px-6 py-8 text-center">
                    <p className="text-sm text-gray-600">
                        Nativity<span className="text-fuchsia-500">.</span>ai © 2024 • Hyper-localizing the Internet for Bharat
                    </p>
                </div>
            </footer>
        </main>
    );
}
