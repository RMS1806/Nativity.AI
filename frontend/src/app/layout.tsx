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
          <meta name="theme-color" content="#000000" />
        </head>
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased bg-black text-gray-100 min-h-screen selection:bg-fuchsia-600/40`}
        >
          {/* Dark Purple Glow - Very Subtle */}
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-900/20 blur-[200px] rounded-full pointer-events-none" />

          {/* Content */}
          <div className="relative z-10">
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
}
