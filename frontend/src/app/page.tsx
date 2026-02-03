"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { FileText, Sparkles, LogIn } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-slate-200">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 px-6 py-4 flex justify-between items-center bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-slate-900" />
          <span className="text-lg font-bold">PDFGenie</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm font-medium hover:text-slate-600 px-3">Sign In</Link>
          <Link href="/signup" className="text-sm font-bold bg-slate-900 text-white px-5 py-2.5 rounded-lg hover:bg-slate-800 transition-colors shadow-sm">Get Started</Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="container mx-auto px-6 pt-32 pb-20 flex flex-col items-center justify-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-3xl"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold uppercase tracking-wider mb-6">
            <span>Powered by Llama 3.2</span>
          </div>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            Intelligent conversations with your PDF documents.
          </h1>
          <p className="text-lg text-slate-500 mb-10 leading-relaxed max-w-2xl mx-auto">
            Upload your files and get instant answers. Perfect for researchers, students, and professionals needing precise information.
          </p>

          <div className="flex flex-col sm:flex-row gap-3 items-center justify-center">
            <Link
              href="/signup"
              className="w-full sm:w-auto px-8 py-3.5 text-base font-bold bg-slate-900 text-white rounded-xl shadow-lg hover:bg-slate-800 transition-all flex items-center justify-center gap-2"
            >
              Start Uploading
              <FileText className="w-4 h-4" />
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-3.5 text-base font-bold bg-white text-slate-900 rounded-xl border border-slate-200 hover:bg-slate-50 transition-all flex items-center justify-center gap-2"
            >
              View Dashboard
            </Link>
          </div>
        </motion.div>

        {/* Simple Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-24 w-full max-w-5xl">
          {[
            { title: "Smart Retrieval", desc: "Instantly finds relevant context within thousands of pages." },
            { title: "Local Indexing", desc: "Secure vector storage using FAISS for privacy and speed." },
            { title: "Direct Answers", desc: "No more scrolling. Get direct answers to your complex questions." }
          ].map((feature, i) => (
            <div key={i} className="p-8 bg-white border border-slate-200 rounded-2xl text-left">
              <h3 className="text-lg font-bold mb-2">{feature.title}</h3>
              <p className="text-slate-500 text-sm leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="py-12 border-t border-slate-200 text-center">
        <p className="text-xs text-slate-400 font-medium">© 2026 PDFGenie. Minimal AI Toolkit.</p>
      </footer>
    </div>
  );
}
