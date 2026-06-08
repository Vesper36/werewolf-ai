import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { Home, Settings, Swords } from "lucide-react";
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
  title: "AI狼人杀 -- 大师竞技场",
  description: "与 AI 对弈的狼人杀大师竞技场",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gray-950 text-gray-100">
        {/* Navigation */}
        <nav className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur-xl border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5 text-gray-100 hover:text-amber-400 transition-colors">
              <Swords size={22} className="text-amber-400" />
              <span className="font-bold text-lg tracking-tight">AI狼人杀</span>
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition-all"
              >
                <Home size={16} />
                <span>大厅</span>
              </Link>
              <Link
                href="/settings"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-gray-100 hover:bg-gray-800 transition-all"
              >
                <Settings size={16} />
                <span>设置</span>
              </Link>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
