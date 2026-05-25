import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter, Space_Grotesk, Space_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

const spaceMono = Space_Mono({
  variable: "--font-space-mono",
  subsets: ["latin"],
  weight: ["400", "700"],
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
      <html lang="en" className="light">
        <head>
          <link rel="icon" href="/favicon.ico" />
          <meta name="theme-color" content="#fff8f1" />
        </head>
        <body
          className={`${inter.variable} ${spaceGrotesk.variable} ${spaceMono.variable} antialiased min-h-screen selection:bg-[#ba061b]/20 selection:text-[#ba061b]`}
          style={{ backgroundColor: '#fff8f1', color: '#1e1b17' }}
        >
          {/* Neo Brutalism dot grid background */}
          <div
            className="fixed inset-0 pointer-events-none"
            style={{
              zIndex: 0,
              backgroundImage: 'radial-gradient(#1A1A1A 1px, transparent 1px)',
              backgroundSize: '24px 24px',
              opacity: 0.06,
            }}
            aria-hidden="true"
          />

          {/* Content */}
          <div className="relative" style={{ zIndex: 1 }}>
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
