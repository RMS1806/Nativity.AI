'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
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

// Animated Button Component
function GlowButton({ children, onClick, className = '', href }: { children: React.ReactNode; onClick?: () => void; className?: string; href?: string }) {
  const buttonContent = (
    <motion.button
      onClick={onClick}
      whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(168, 85, 247, 0.4)' }}
      whileTap={{ scale: 0.98 }}
      className={`relative overflow-hidden group px-8 py-4 bg-gradient-to-r from-fuchsia-600 via-purple-600 to-violet-600 text-white text-lg font-bold rounded-xl transition-all duration-300 ${className}`}
    >
      {/* Shimmer effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full"
        animate={{ translateX: ['−100%', '100%'] }}
        transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
      />
      <span className="relative z-10 flex items-center gap-3">{children}</span>
    </motion.button>
  );

  if (href) {
    return <Link href={href}>{buttonContent}</Link>;
  }
  return buttonContent;
}

// Hero Section - Pure Dark Tech Theme
function HeroSection() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center min-h-[75vh] text-center px-4"
    >
      <div className="max-w-4xl mx-auto">
        {/* Terminal-style Badge */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-lg bg-gray-900 border border-gray-800"
        >
          <Terminal className="w-4 h-4 text-fuchsia-500" />
          <span className="text-sm font-mono text-gray-300">
            <span className="text-fuchsia-500">$</span> powered_by <span className="text-purple-400">Gemini AI</span>
          </span>
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 leading-tight"
        >
          <span className="text-white">Hyper-localize your</span>
          <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-500 via-purple-500 to-violet-500">
            videos for Bharat
          </span>
        </motion.h1>

        {/* Subhead */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto"
        >
          AI-powered dubbing in{' '}
          <span className="text-white font-semibold">Hindi</span>,{' '}
          <span className="text-white font-semibold">Tamil</span>, and{' '}
          <span className="text-white font-semibold">Bengali</span>.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <SignInButton mode="modal">
            <GlowButton>
              <Zap className="w-5 h-5" />
              Get Started
              <ArrowRight className="w-5 h-5" />
            </GlowButton>
          </SignInButton>
        </motion.div>

        {/* Feature Cards - Dark Tech Style */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex flex-wrap justify-center gap-4 mt-16"
        >
          {[
            { icon: Play, label: 'Video Analysis', color: 'text-fuchsia-500' },
            { icon: Globe, label: 'Cultural Adaptation', color: 'text-purple-500' },
            { icon: Mic, label: 'Natural TTS', color: 'text-violet-500' },
          ].map((feature, index) => (
            <motion.div
              key={feature.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 + index * 0.1 }}
              whileHover={{ scale: 1.05, borderColor: 'rgba(168, 85, 247, 0.5)' }}
              className="flex items-center gap-3 px-5 py-3 bg-gray-900/80 border border-gray-800 rounded-xl cursor-default transition-colors"
            >
              <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center justify-center">
                <feature.icon className={`w-4 h-4 ${feature.color}`} />
              </div>
              <span className="text-sm text-gray-300 font-medium">{feature.label}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </motion.div>
  );
}

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
    }, 3000); // Poll every 3 seconds

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

            <div className="flex items-center gap-3">
              <SignedIn>
                {appState !== 'IDLE' && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={handleReset}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg transition-all"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Start Over
                  </motion.button>
                )}
                <Link href="/dashboard">
                  <motion.div
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-400 hover:text-white bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-lg transition-all"
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
                    whileHover={{ scale: 1.05, boxShadow: '0 0 20px rgba(168, 85, 247, 0.3)' }}
                    whileTap={{ scale: 0.95 }}
                    className="px-4 py-2 text-sm font-bold text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 rounded-lg transition-all"
                  >
                    Sign In
                  </motion.button>
                </SignInButton>
              </SignedOut>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <SignedOut>
          <HeroSection />
        </SignedOut>

        <SignedIn>
          {appState === 'IDLE' && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              <div className="text-center max-w-2xl mx-auto">
                <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                  Localize your videos for{' '}
                  <span className="bg-clip-text text-transparent bg-gradient-to-r from-fuchsia-500 to-purple-500">
                    Bharat
                  </span>
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
                  initial={{ opacity: 0, scale: 0.95 }}
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
            <UploadZone onFileSelect={() => { }} isUploading={true} uploadProgress={uploadProgress} />
          )}

          {appState === 'PROCESSING' && currentJob && (
            <ProcessingStatus status={currentJob.status} progress={currentJob.progress} message={currentJob.message} />
          )}

          {appState === 'COMPLETED' && currentJob && <ResultCard job={currentJob} />}

          {appState === 'ERROR' && (
            <div className="text-center max-w-md mx-auto">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-900/30 border border-red-800 flex items-center justify-center">
                <span className="text-4xl">😞</span>
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Something went wrong</h2>
              <p className="text-gray-400 mb-6">{error}</p>
              <GlowButton onClick={handleReset}>
                Try Again
              </GlowButton>
            </div>
          )}
        </SignedIn>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-900 mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-8 text-center">
          <p className="text-sm text-gray-500">
            Built with ❤️ for Bharat • Powered by{' '}
            <span className="text-fuchsia-500">Gemini AI</span> &{' '}
            <span className="text-purple-500">AWS</span>
          </p>
        </div>
      </footer>
    </main>
  );
}
