import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Nativity.ai - Hyper-localizing the Internet for Bharat",
  description: "Transform English videos into culturally-adapted Hindi, Tamil, Bengali & more using AI. Powered by Google Gemini and AWS.",
  keywords: ["video localization", "dubbing", "AI", "India", "hindi", "tamil", "bengali", "gemini"],
  openGraph: {
    title: "Nativity.ai",
    description: "Hyper-localizing the Internet for Bharat, one video at a time.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        <head>
          <link rel="icon" href="/favicon.ico" />
          <meta name="theme-color" content="#050505" />
        </head>
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen selection:bg-[#00E5FF]/20 selection:text-[#00E5FF]`}
          style={{ backgroundColor: '#050505', color: '#e2e8f0' }}
        >
          {/* Ambient gradient orbs — deep void background */}
          <div
            className="fixed inset-0 pointer-events-none overflow-hidden"
            style={{ zIndex: 0 }}
            aria-hidden="true"
          >
            {/* Primary: deep purple center bloom */}
            <div
              className="absolute"
              style={{
                top: '10%',
                left: '50%',
                transform: 'translateX(-50%)',
                width: '900px',
                height: '700px',
                background: 'radial-gradient(ellipse at center, rgba(88, 28, 220, 0.18) 0%, transparent 70%)',
                filter: 'blur(60px)',
              }}
            />
            {/* Cyan accent — top-left */}
            <div
              className="absolute"
              style={{
                top: '-5%',
                left: '-5%',
                width: '600px',
                height: '600px',
                background: 'radial-gradient(ellipse at center, rgba(0, 229, 255, 0.07) 0%, transparent 70%)',
                filter: 'blur(80px)',
              }}
            />
            {/* Magenta accent — bottom-right */}
            <div
              className="absolute"
              style={{
                bottom: '-10%',
                right: '-5%',
                width: '700px',
                height: '700px',
                background: 'radial-gradient(ellipse at center, rgba(255, 0, 255, 0.07) 0%, transparent 70%)',
                filter: 'blur(80px)',
              }}
            />
            {/* Volt green — subtle, bottom-left */}
            <div
              className="absolute"
              style={{
                bottom: '15%',
                left: '5%',
                width: '400px',
                height: '400px',
                background: 'radial-gradient(ellipse at center, rgba(204, 255, 0, 0.04) 0%, transparent 70%)',
                filter: 'blur(60px)',
              }}
            />
          </div>

          {/* Content */}
          <div className="relative" style={{ zIndex: 1 }}>
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
