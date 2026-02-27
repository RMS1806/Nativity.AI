'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { Sparkles, ArrowRight, RefreshCw, LayoutDashboard, Play, Globe, Mic, Zap, Terminal } from 'lucide-react';
import { SignInButton, SignedIn, SignedOut, UserButton, useAuth } from '@clerk/nextjs';
import Link from 'next/link';

import UploadZone from '@/components/UploadZone';
import ProcessingStatus from '@/components/ProcessingStatus';
import ResultCard from '@/components/ResultCard';
import LanguageSelector from '@/components/LanguageSelector';

import {
  getUploadUrl,
  uploadToS3,
  startLocalization,
  getJobStatus,
  getLanguages
} from '@/lib/api';
import { AppState, Language, LocalizationJob, JobStatus } from '@/types';

// ─── Neon Glow Button ────────────────────────────────────────────────
function GlowButton({ children, onClick, className = '', href }: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  href?: string;
}) {
  const buttonContent = (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.05, boxShadow: '0 0 50px rgba(0, 229, 255, 0.4)' }}
      whileTap={{ scale: 0.97 }}
      className={`relative overflow-hidden group px-8 py-4 text-white text-lg font-bold rounded-xl transition-all duration-300 ${className}`}
      style={{
        background: 'linear-gradient(135deg, #00E5FF 0%, #9000FF 50%, #FF00FF 100%)',
        boxShadow: '0 0 30px rgba(0, 229, 255, 0.25)',
      }}
    >
      {/* Shimmer */}
      <span
        className="shimmer-overlay rounded-xl"
        style={{ animationDuration: '2.5s' }}
      />
      <span className="relative z-10 flex items-center gap-3">{children}</span>
    </motion.button>
  );

  if (href) return <Link href={href}>{buttonContent}</Link>;
  return buttonContent;
}

// ─── Hero Section ─────────────────────────────────────────────────────
function HeroSection() {
  const containerVariants: Variants = {
    hidden: {},
    show: {
      transition: { staggerChildren: 0.12 },
    },
  };

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 30 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] as const },
    },
  };

  const features = [
    { icon: Play, label: 'Video Analysis', color: '#00E5FF' },
    { icon: Globe, label: 'Cultural Adaptation', color: '#FF00FF' },
    { icon: Mic, label: 'Natural TTS', color: '#CCFF00' },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center px-4">
      <div className="max-w-4xl mx-auto">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.05, duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-lg"
          style={{
            background: 'rgba(255,255,255,0.05)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(0,229,255,0.2)',
          }}
        >
          <Terminal className="w-4 h-4" style={{ color: '#00E5FF' }} />
          <span className="text-sm font-mono text-gray-300">
            <span style={{ color: '#00E5FF' }}>$</span> powered_by{' '}
            <span style={{ color: '#FF00FF' }}>Gemini AI</span>
          </span>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-4"
        >
          {/* Headline */}
          <motion.h1
            variants={itemVariants}
            className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-tight"
          >
            <span className="text-white">Hyper-localize your</span>
            <br />
            <span className="neon-text-gradient">videos for Bharat</span>
          </motion.h1>

          {/* Subhead */}
          <motion.p
            variants={itemVariants}
            className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto"
          >
            AI-powered dubbing in{' '}
            <span className="text-white font-semibold">Hindi</span>,{' '}
            <span className="text-white font-semibold">Tamil</span>, and{' '}
            <span className="text-white font-semibold">Bengali</span>.
          </motion.p>

          {/* CTA */}
          <motion.div variants={itemVariants}>
            <SignInButton mode="modal">
              <GlowButton>
                <Zap className="w-5 h-5" />
                Get Started
                <ArrowRight className="w-5 h-5" />
              </GlowButton>
            </SignInButton>
          </motion.div>
        </motion.div>

        {/* Feature Cards */}
        <div className="flex flex-wrap justify-center gap-4 mt-16">
          {features.map((feature, index) => (
            <motion.div
              key={feature.label}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.12, duration: 0.5 }}
              whileHover={{ scale: 1.06, y: -3 }}
              className="flex items-center gap-3 px-5 py-3 rounded-xl cursor-default"
              style={{
                background: 'rgba(255,255,255,0.05)',
                backdropFilter: 'blur(12px)',
                border: `1px solid rgba(255,255,255,0.08)`,
                transition: 'border-color 0.3s',
              }}
            >
              <div
                className="w-9 h-9 rounded-lg flex items-center justify-center"
                style={{ background: `${feature.color}18` }}
              >
                <feature.icon className="w-4 h-4" style={{ color: feature.color }} />
              </div>
              <span className="text-sm text-gray-300 font-medium">{feature.label}</span>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────
export default function Home() {
  const { getToken } = useAuth();
  const [appState, setAppState] = useState<AppState>('IDLE');
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [fileKey, setFileKey] = useState<string | null>(null);

  const [languages, setLanguages] = useState<Language[]>([
    { code: 'hindi', name: 'Hindi', native: 'हिंदी' },
    { code: 'tamil', name: 'Tamil', native: 'தமிழ்' },
    { code: 'bengali', name: 'Bengali', native: 'বাংলা' },
    { code: 'telugu', name: 'Telugu', native: 'తెలుగు' },
    { code: 'marathi', name: 'Marathi', native: 'मराठी' },
  ]);
  const [selectedLanguage, setSelectedLanguage] = useState('hindi');
  const [currentJob, setCurrentJob] = useState<LocalizationJob | null>(null);

  useEffect(() => {
    getLanguages()
      .then(data => setLanguages(data.languages))
      .catch(() => { });
  }, []);

  useEffect(() => {
    if (appState !== 'PROCESSING' || !currentJob?.job_id) return;

    const pollInterval = setInterval(async () => {
      try {
        const job = await getJobStatus(currentJob.job_id);
        setCurrentJob(job);
        if (job.status === 'complete') {
          setAppState('COMPLETED');
          clearInterval(pollInterval);
        } else if (job.status === 'failed') {
          setError(job.error || 'Processing failed');
          setAppState('ERROR');
          clearInterval(pollInterval);
        }
      } catch (err) {
        console.error('Failed to poll job status:', err);
      }
    }, 3000);

    return () => clearInterval(pollInterval);
  }, [appState, currentJob?.job_id]);

  const handleFileSelect = useCallback((file: File) => {
    setSelectedFile(file);
    setError(null);
  }, []);

  const handleStartProcessing = async () => {
    if (!selectedFile) return;
    try {
      setAppState('UPLOADING');
      setUploadProgress(0);

      const token = await getToken();
      if (!token) throw new Error('Please sign in to upload videos');

      const uploadData = await getUploadUrl(selectedFile.name, selectedFile.type, token);
      await uploadToS3(uploadData.upload_url, selectedFile, setUploadProgress);

      setFileKey(uploadData.file_key);
      setUploadProgress(100);
      setAppState('PROCESSING');

      const response = await startLocalization(uploadData.file_key, selectedLanguage, token);
      setCurrentJob({
        job_id: response.job_id,
        status: 'pending' as JobStatus,
        progress: 0,
        message: response.message,
        input_file: uploadData.file_key,
        target_language: selectedLanguage,
      });
    } catch (err: any) {
      console.error('Processing error:', err);
      setError(err.response?.data?.detail || err.message || 'An error occurred');
      setAppState('ERROR');
    }
  };

  const handleReset = () => {
    setAppState('IDLE');
    setSelectedFile(null);
    setUploadProgress(0);
    setFileKey(null);
    setCurrentJob(null);
    setError(null);
  };

  return (
    <main className="min-h-screen flex flex-col">
      {/* ── Floating Glass Navbar ─────────────────────────────── */}
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

          {/* Nav Actions */}
          <div className="flex items-center gap-3">
            <SignedIn>
              {appState !== 'IDLE' && (
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={handleReset}
                  className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white rounded-full transition-all"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  <RefreshCw className="w-4 h-4" />
                  Start Over
                </motion.button>
              )}
              <Link href="/dashboard">
                <motion.div
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-400 hover:text-white rounded-full transition-all"
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)' }}
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </motion.div>
              </Link>
              <UserButton afterSignOutUrl="/" />
            </SignedIn>

            <SignedOut>
              <SignInButton mode="modal">
                <motion.button
                  whileHover={{ scale: 1.05, boxShadow: '0 0 25px rgba(0,229,255,0.4)' }}
                  whileTap={{ scale: 0.95 }}
                  className="px-5 py-2 text-sm font-bold text-black rounded-full transition-all"
                  style={{ background: 'linear-gradient(135deg, #00E5FF, #FF00FF)' }}
                >
                  Sign In
                </motion.button>
              </SignInButton>
            </SignedOut>
          </div>
        </nav>
      </div>

      {/* ── Main Content ──────────────────────────────────────── */}
      <div className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        <SignedOut>
          <HeroSection />
        </SignedOut>

        <SignedIn>
          <AnimatePresence mode="wait">
            {appState === 'IDLE' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="space-y-8"
              >
                <div className="text-center max-w-2xl mx-auto">
                  <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                    Localize your videos for{' '}
                    <span className="neon-text-gradient">Bharat</span>
                  </h2>
                  <p className="text-lg text-gray-400">
                    Transform English content into culturally-adapted regional languages
                  </p>
                </div>

                <div className="max-w-xs mx-auto">
                  <label className="block text-sm font-medium text-gray-400 mb-2 text-center">
                    Target Language
                  </label>
                  <LanguageSelector
                    languages={languages}
                    selected={selectedLanguage}
                    onChange={setSelectedLanguage}
                  />
                </div>

                <UploadZone
                  onFileSelect={handleFileSelect}
                  isUploading={false}
                  uploadProgress={0}
                />

                {selectedFile && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex justify-center"
                  >
                    <GlowButton onClick={handleStartProcessing}>
                      <Sparkles className="w-5 h-5" />
                      Start Localization
                      <ArrowRight className="w-5 h-5" />
                    </GlowButton>
                  </motion.div>
                )}
              </motion.div>
            )}

            {appState === 'UPLOADING' && (
              <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <UploadZone onFileSelect={() => { }} isUploading={true} uploadProgress={uploadProgress} />
              </motion.div>
            )}

            {appState === 'PROCESSING' && currentJob && (
              <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <ProcessingStatus status={currentJob.status} progress={currentJob.progress} message={currentJob.message} />
              </motion.div>
            )}

            {appState === 'COMPLETED' && currentJob && (
              <motion.div key="completed" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <ResultCard job={currentJob} />
              </motion.div>
            )}

            {appState === 'ERROR' && (
              <motion.div
                key="error"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center max-w-md mx-auto"
              >
                <div
                  className="rounded-2xl p-8 space-y-4"
                  style={{
                    background: 'rgba(255,0,0,0.05)',
                    border: '1px solid rgba(255,60,60,0.3)',
                    backdropFilter: 'blur(12px)',
                  }}
                >
                  <div
                    className="w-20 h-20 mx-auto rounded-full flex items-center justify-center"
                    style={{ background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.3)' }}
                  >
                    <span className="text-4xl">😞</span>
                  </div>
                  <h2 className="text-2xl font-bold text-white">Something went wrong</h2>
                  <p className="text-gray-400">{error}</p>
                  <GlowButton onClick={handleReset}>Try Again</GlowButton>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </SignedIn>
      </div>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <footer style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }} className="mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-8 text-center">
          <p className="text-sm text-gray-600">
            Built with ❤️ for Bharat • Powered by{' '}
            <span style={{ color: '#00E5FF' }}>Gemini AI</span>{' '}
            &{' '}
            <span style={{ color: '#FF00FF' }}>AWS</span>
          </p>
        </div>
      </footer>
    </main>
  );
}
