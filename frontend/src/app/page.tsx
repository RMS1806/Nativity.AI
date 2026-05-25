'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import { Sparkles, ArrowRight, RefreshCw, LayoutDashboard, Play, Globe, Mic, Zap, Search } from 'lucide-react';
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

// ─── Neo Brutal Button ────────────────────────────────────────────────
function NeoButton({ children, onClick, className = '', href, variant = 'primary' }: {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  href?: string;
  variant?: 'primary' | 'secondary' | 'outline';
}) {
  const baseClasses = 'relative overflow-hidden px-8 py-4 text-lg font-bold neo-border neo-shadow neo-shadow-hover neo-shadow-active transition-all duration-200 font-headline flex items-center gap-3';
  const variantClasses = {
    primary: 'bg-[#ba061b] text-white',
    secondary: 'bg-[#8127cf] text-white',
    outline: 'bg-white text-[#1A1A1A]',
  };

  const buttonContent = (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
    >
      {children}
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
    { icon: Search, label: 'Video Analysis', color: '#BFFF00' },
    { icon: Globe, label: 'Cultural Adaptation', color: '#FBBF24' },
    { icon: Mic, label: 'Natural TTS', color: '#FF2D78' },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center px-4">
      <div className="max-w-4xl mx-auto">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.05, duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 neo-border neo-shadow bg-[#F3EDFF]"
          style={{ borderRadius: '9999px' }}
        >
          <span className="text-xl">⚡</span>
          <span className="font-mono-label text-[#8127cf] font-bold">
            Powered by Gemini AI
          </span>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="space-y-6"
        >
          {/* Headline */}
          <motion.h1
            variants={itemVariants}
            className="text-4xl sm:text-5xl lg:text-[64px] font-bold leading-tight font-headline"
            style={{ letterSpacing: '-0.02em' }}
          >
            <span className="text-[#1A1A1A]">Hyper-localize your videos for </span>
            <span
              className="text-[#ba061b] inline-block bg-white px-3 neo-border neo-shadow"
              style={{ transform: 'rotate(-2deg)' }}
            >
              Bharat
            </span>
          </motion.h1>

          {/* Subhead */}
          <motion.p
            variants={itemVariants}
            className="text-lg text-[#5c403d] mb-10 max-w-2xl mx-auto"
          >
            Break language barriers with raw, authentic video translation. Neo-brutal accuracy meets cultural nuance for the next billion users.
          </motion.p>

          {/* CTA */}
          <motion.div variants={itemVariants} className="pt-4">
            <SignInButton mode="modal">
              <motion.button
                whileHover={{ rotate: 0, y: -2, x: -2 }}
                whileTap={{ y: 4, x: 4 }}
                className="inline-flex items-center gap-2 px-8 py-4 bg-[#ba061b] text-white font-bold text-xl neo-border font-headline"
                style={{
                  transform: 'rotate(-1deg)',
                  boxShadow: '4px 4px 0px 0px #1A1A1A',
                  transition: 'all 0.2s ease',
                }}
              >
                Get Started
                <ArrowRight className="w-5 h-5" />
              </motion.button>
            </SignInButton>
          </motion.div>
        </motion.div>

        {/* Feature Cards */}
        <div className="flex flex-wrap justify-center gap-6 mt-20">
          {features.map((feature, index) => {
            const rotations = [1, -2, 2];
            return (
              <motion.div
                key={feature.label}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 + index * 0.12, duration: 0.5 }}
                whileHover={{ rotate: 0, y: -8 }}
                className="bg-white neo-border neo-shadow p-8 flex flex-col items-start gap-4 w-64 cursor-default"
                style={{ transform: `rotate(${rotations[index]}deg)`, transition: 'transform 0.3s, box-shadow 0.3s' }}
              >
                <div
                  className="w-12 h-12 neo-border neo-shadow flex items-center justify-center"
                  style={{ backgroundColor: feature.color }}
                >
                  <feature.icon className="w-5 h-5 text-[#1A1A1A]" />
                </div>
                <span className="text-xl font-bold font-headline text-[#1A1A1A]">{feature.label}</span>
                <p className="text-sm text-[#5c403d]">
                  {index === 0 && 'Deep context extraction beyond literal translation. We analyze slang, tone, and pacing.'}
                  {index === 1 && 'Rewrite scripts to resonate with local idioms and cultural references.'}
                  {index === 2 && 'Hyper-realistic voice synthesis that matches the original speaker\'s emotion.'}
                </p>
              </motion.div>
            );
          })}
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
      {/* ── Neo Brutal Navbar ─────────────────────────────── */}
      <div className="sticky top-0 z-50">
        <nav
          className="flex items-center justify-between px-4 md:px-10 h-20 bg-white"
          style={{
            borderBottom: '3px solid #1A1A1A',
          }}
        >
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <motion.div
              whileHover={{ rotate: 12, scale: 1.1 }}
              transition={{ duration: 0.3 }}
              className="w-10 h-10 flex items-center justify-center neo-border"
              style={{
                backgroundColor: '#ba061b',
                boxShadow: '4px 4px 0px 0px #1A1A1A',
              }}
            >
              <Zap className="w-5 h-5 text-white" />
            </motion.div>
            <span className="text-xl font-bold font-headline text-[#1A1A1A] tracking-tight">
              Nativity.ai
            </span>
          </Link>

          {/* Nav Actions */}
          <div className="flex items-center gap-3">
            <SignedIn>
              {appState !== 'IDLE' && (
                <motion.button
                  whileHover={{ y: -2, x: -2 }}
                  whileTap={{ y: 2, x: 2 }}
                  onClick={handleReset}
                  className="flex items-center gap-2 px-4 py-2 font-mono-label text-[#1A1A1A] neo-border bg-white transition-all"
                  style={{ boxShadow: '3px 3px 0px 0px #1A1A1A' }}
                >
                  <RefreshCw className="w-4 h-4" />
                  Start Over
                </motion.button>
              )}
              <Link href="/dashboard">
                <motion.div
                  whileHover={{ y: -2, x: -2 }}
                  whileTap={{ y: 2, x: 2 }}
                  className="flex items-center gap-2 px-4 py-2 font-mono-label text-[#1A1A1A] neo-border bg-white transition-all"
                  style={{ boxShadow: '3px 3px 0px 0px #1A1A1A' }}
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
                  whileHover={{ y: -2, x: -2 }}
                  whileTap={{ y: 2, x: 2 }}
                  className="px-6 py-2 font-mono-label font-bold text-white neo-border transition-all"
                  style={{
                    backgroundColor: '#8127cf',
                    boxShadow: '4px 4px 0px 0px #1A1A1A',
                  }}
                >
                  Sign In
                </motion.button>
              </SignInButton>
            </SignedOut>
          </div>
        </nav>
      </div>

      {/* ── Main Content ──────────────────────────────────── */}
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
                  <h2 className="text-3xl sm:text-4xl font-bold text-[#1A1A1A] mb-4 font-headline">
                    Localize your videos for{' '}
                    <span className="text-[#ba061b]">Bharat</span>
                  </h2>
                  <p className="text-lg text-[#5c403d]">
                    Transform English content into culturally-adapted regional languages
                  </p>
                </div>

                <div className="max-w-lg mx-auto">
                  <label className="block font-mono-label text-[#5c403d] mb-3 text-center uppercase tracking-wider">
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
                    <motion.button
                      onClick={handleStartProcessing}
                      whileHover={{ rotate: 0, y: -2, x: -2 }}
                      whileTap={{ y: 4, x: 4 }}
                      className="inline-flex items-center gap-2 px-8 py-4 bg-[#ba061b] text-white font-bold text-xl neo-border font-headline"
                      style={{
                        transform: 'rotate(-1deg)',
                        boxShadow: '4px 4px 0px 0px #1A1A1A',
                        transition: 'all 0.2s ease',
                      }}
                    >
                      <Sparkles className="w-5 h-5" />
                      Start Localization
                      <ArrowRight className="w-5 h-5" />
                    </motion.button>
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
                  className="neo-border neo-shadow-lg p-8 space-y-4 bg-white"
                >
                  <div
                    className="w-20 h-20 mx-auto neo-border neo-shadow flex items-center justify-center"
                    style={{ backgroundColor: '#FF2D78' }}
                  >
                    <span className="text-4xl">😞</span>
                  </div>
                  <h2 className="text-2xl font-bold text-[#1A1A1A] font-headline">Something went wrong</h2>
                  <p className="text-[#5c403d]">{error}</p>
                  <motion.button
                    onClick={handleReset}
                    whileHover={{ y: -2, x: -2 }}
                    whileTap={{ y: 2, x: 2 }}
                    className="px-6 py-3 bg-[#ba061b] text-white font-bold neo-border font-mono-label uppercase tracking-wider"
                    style={{ boxShadow: '4px 4px 0px 0px #1A1A1A' }}
                  >
                    Try Again
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </SignedIn>
      </div>

      {/* ── Footer ──────────────────────────────────────────── */}
      <footer
        className="mt-auto"
        style={{ borderTop: '3px solid #1A1A1A', backgroundColor: '#e8e1da' }}
      >
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="text-xl font-bold font-headline text-[#ba061b] flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Nativity.ai
          </div>
          <div className="font-mono-label flex gap-6 text-[#5c403d]">
            <a className="hover:text-[#ba061b] transition-colors hover:underline decoration-[3px] underline-offset-4" href="#">Privacy</a>
            <a className="hover:text-[#ba061b] transition-colors hover:underline decoration-[3px] underline-offset-4" href="#">Terms</a>
            <a className="hover:text-[#ba061b] transition-colors hover:underline decoration-[3px] underline-offset-4" href="#">Support</a>
          </div>
          <div
            className="font-bold bg-white px-4 py-2 neo-border neo-shadow"
            style={{ transform: 'rotate(-1deg)' }}
          >
            Built with ❤️ for Bharat
          </div>
        </div>
      </footer>
    </main>
  );
}
