"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
    Upload,
    Send,
    LogOut,
    FileText,
    Plus,
    Search,
    MessageSquare,
    Loader2,
    CheckCircle2,
    User,
    LayoutDashboard,
    Trash2
} from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

type Message = {
    role: "user" | "ai";
    content: string;
};

type Document = {
    id: number;
    filename: string;
    user_id: number;
};

export default function Dashboard() {
    const { logout } = useAuth();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [selectedIds, setSelectedIds] = useState<number[]>([]);
    const [uploading, setUploading] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState(false);
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [sending, setSending] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // 1. Fetch documents on mount
    const fetchDocuments = async () => {
        try {
            const { data } = await api.get("/documents");
            setDocuments(data);
            // Auto-select the first document if none selected
            if (data.length > 0 && selectedIds.length === 0) {
                setSelectedIds([data[0].id]);
            }
        } catch (err) {
            console.error("Failed to fetch documents", err);
        }
    };

    const handleDeleteDocument = async (e: React.MouseEvent, docId: number) => {
        e.stopPropagation(); // Don't trigger the selection toggle
        if (!confirm("Are you sure you want to delete this document?")) return;

        try {
            await api.delete(`/documents/${docId}`);
            // Refresh list
            await fetchDocuments();
            // Remove from selected if it was there
            setSelectedIds(prev => prev.filter(id => id !== docId));
        } catch (err) {
            console.error("Delete failed", err);
            alert("Failed to delete document.");
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, []);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (!selectedFile) return;

        setUploading(true);
        setUploadSuccess(false);

        const formData = new FormData();
        formData.append("file", selectedFile);

        try {
            const { data } = await api.post("/upload-pdf", formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setUploadSuccess(true);
            // Refresh list and select the new one
            await fetchDocuments();
            setSelectedIds(prev => [...prev, data.id]);
        } catch (err) {
            console.error("Upload failed", err);
        } finally {
            setUploading(false);
            // Reset the input value so the same file can be uploaded again
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    const handleSendMessage = async () => {
        if (!input.trim() || sending) return;
        if (selectedIds.length === 0) {
            alert("Please select at least one document from the sidebar.");
            return;
        }

        const userMessage = input.trim();
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setInput("");
        setSending(true);

        try {
            const { data } = await api.post("/ask", {
                question: userMessage,
                pdf_ids: selectedIds
            });
            setMessages((prev) => [...prev, { role: "ai", content: data.answer }]);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "ai", content: "Sorry, I encountered an error. Make sure your documents are selected." }]);
        } finally {
            setSending(false);
        }
    };

    return (
        <div className="flex h-screen bg-slate-50 text-slate-900 overflow-hidden font-sans">
            {/* Sidebar - Clean Slate Style */}
            <aside className="w-72 border-r border-slate-200 bg-white flex flex-col p-6 overflow-hidden">
                <div className="flex items-center gap-2 mb-8 px-2">
                    <LayoutDashboard className="w-5 h-5 text-slate-900" />
                    <span className="text-lg font-bold tracking-tight">PDFGenie</span>
                </div>

                <button className="flex items-center gap-2 w-full p-2.5 px-4 rounded-lg bg-slate-900 text-white text-sm font-bold hover:bg-slate-800 transition-all mb-8 shadow-sm">
                    <Plus className="w-4 h-4" />
                    New Chat
                </button>

                <div className="flex-1 space-y-1 overflow-y-auto overflow-x-hidden">
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest px-2 mb-3">Library</p>
                    {documents.length === 0 ? (
                        <p className="text-center text-xs text-slate-400 p-4">No documents yet.</p>
                    ) : (
                        documents.map((doc) => (
                            <div
                                key={doc.id}
                                onClick={() => {
                                    setSelectedIds(prev =>
                                        prev.includes(doc.id)
                                            ? prev.filter(id => id !== doc.id)
                                            : [...prev, doc.id]
                                    );
                                }}
                                className={`p-3 rounded-lg flex items-center gap-3 transition-colors cursor-pointer group ${selectedIds.includes(doc.id) ? "bg-slate-100 font-bold" : "hover:bg-slate-50"}`}
                            >
                                <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${selectedIds.includes(doc.id) ? "bg-slate-900 border-slate-900" : "border-slate-300"}`}>
                                    {selectedIds.includes(doc.id) && <div className="w-1.5 h-1.5 bg-white rounded-full" />}
                                </div>
                                <span className="text-xs truncate flex-1">{doc.filename}</span>
                                <button
                                    onClick={(e) => handleDeleteDocument(e, doc.id)}
                                    className="p-1.5 opacity-0 group-hover:opacity-100 hover:bg-slate-200 rounded text-slate-400 hover:text-red-600 transition-all"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        ))
                    )}
                </div>

                <div className="mt-auto pt-6 border-t border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-3 px-1">
                        <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-bold text-xs uppercase">MQ</div>
                        <div className="text-xs font-bold truncate max-w-[120px]">Muneeb Qazi</div>
                    </div>
                    <button onClick={logout} className="p-2 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors">
                        <LogOut className="w-4 h-4" />
                    </button>
                </div>
            </aside>

            {/* Main Workspace */}
            <main className="flex-1 flex flex-col min-w-0">
                {/* Header */}
                <header className="h-16 px-8 flex items-center justify-between bg-white border-b border-slate-200">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-slate-100 rounded-lg">
                            <FileText className="w-4 h-4 text-slate-600" />
                        </div>
                        <h2 className="text-sm font-bold truncate">
                            {selectedIds.length === 0
                                ? "No Selection"
                                : selectedIds.length === 1
                                    ? `Context: ${documents.find(d => d.id === selectedIds[0])?.filename}`
                                    : `${selectedIds.length} Documents Selected`}
                        </h2>
                    </div>
                    <div className="hidden sm:flex items-center gap-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                            <input
                                type="text"
                                placeholder="Search..."
                                className="bg-slate-50 border border-slate-200 rounded-lg py-1.5 pl-9 pr-4 text-xs outline-none w-48 focus:ring-1 focus:ring-slate-400 transition-all"
                            />
                        </div>
                    </div>
                </header>

                {/* Chat Content Area */}
                <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-10 space-y-6 max-w-4xl mx-auto w-full">
                    {messages.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-center py-20">
                            <div className="w-12 h-12 bg-slate-100 rounded-xl flex items-center justify-center text-slate-400 mb-6">
                                <MessageSquare className="w-6 h-6" />
                            </div>
                            <h3 className="text-xl font-bold mb-2">How can I help you today?</h3>
                            <p className="text-slate-500 text-sm max-w-xs mx-auto">Upload a document and ask me anything about its content.</p>
                        </div>
                    ) : (
                        messages.map((m, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : "flex-row"}`}
                            >
                                <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-xs font-bold ${m.role === "ai" ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-600 uppercase"}`}>
                                    {m.role === "ai" ? "AI" : "MQ"}
                                </div>
                                <div className={`p-4 px-5 rounded-2xl text-[13px] leading-relaxed max-w-[85%] ${m.role === "ai" ? "bg-white border border-slate-200 shadow-sm" : "bg-slate-100"}`}>
                                    {m.content}
                                </div>
                            </motion.div>
                        ))
                    )}
                    {sending && (
                        <div className="flex gap-4">
                            <div className="w-8 h-8 rounded-lg bg-slate-200 flex items-center justify-center animate-pulse">
                                <Loader2 className="w-3 h-3 animate-spin" />
                            </div>
                            <div className="bg-slate-50 text-slate-400 text-xs italic p-4">Analysing document...</div>
                        </div>
                    )}
                </div>

                {/* Input Bar Section */}
                <div className="px-6 pb-8 pt-4">
                    <div className="max-w-4xl mx-auto relative group">
                        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-1.5 flex items-center gap-2 group-focus-within:border-slate-400 transition-colors">
                            <label className="p-3 hover:bg-slate-50 rounded-lg cursor-pointer transition-colors text-slate-400 hover:text-slate-900">
                                <input
                                    type="file"
                                    className="hidden"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    accept=".pdf"
                                />
                                <Upload className="w-5 h-5" />
                            </label>

                            <textarea
                                rows={1}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSendMessage();
                                    }
                                }}
                                placeholder="Ask a question..."
                                className="flex-1 bg-transparent py-3 px-1 text-sm outline-none resize-none max-h-32 text-slate-900 placeholder:text-slate-400"
                            />

                            <button
                                onClick={handleSendMessage}
                                disabled={!input.trim() || sending}
                                className="p-3 bg-slate-900 text-white rounded-lg hover:bg-slate-800 disabled:opacity-30 transition-all shadow-sm"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>

                        {uploading && (
                            <div className="absolute -top-10 left-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
                                <Loader2 className="w-3 h-3 animate-spin" />
                                Parsing Document...
                            </div>
                        )}

                        {uploadSuccess && !uploading && (
                            <div className="absolute -top-10 left-4 text-[10px] font-bold text-emerald-600 uppercase tracking-widest flex items-center gap-2">
                                <CheckCircle2 className="w-3 h-3" />
                                Index Optimized
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
