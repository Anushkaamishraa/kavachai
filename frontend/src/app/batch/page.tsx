
"use client";

import React, { useState } from "react";
import axios from "axios";
import { Shield, FileStack, ShieldCheck, ShieldAlert, Zap, LayoutDashboard, History, Settings, LogOut, Bell, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import BatchUpload from "@/components/BatchUpload";
import ResultsTable, { AnalysisResult } from "@/components/ResultsTable";
import ChatAssistant from "@/components/ChatAssistant";

const API_BASE = "http://localhost:8000/api";

export default function BatchAnalysisPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [results, setResults] = useState<AnalysisResult[]>([]);
  const [activeContext, setActiveContext] = useState<any>(null);

  const handleFilesSelected = (newFiles: File[]) => {
    setSelectedFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUploadAll = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    const processingResults: AnalysisResult[] = selectedFiles.map((file, i) => ({
      file_id: `processing-${i}-${Date.now()}`,
      filename: file.name,
      trust_score: 0,
      risk: "medium",
      status: "processing"
    }));
    setResults(processingResults);

    const formData = new FormData();
    selectedFiles.forEach((file) => formData.append("files", file));

    try {
      const response = await axios.post(`${API_BASE}/batch`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = response.data.map((r: any) => ({ ...r, status: "completed" }));
      setResults(data);
      
      const criticalResult = data.find((r: any) => r.risk === "high") || data[0];
      if (criticalResult) {
        setActiveContext({
          trust_score: criticalResult.trust_score,
          risk: criticalResult.risk,
          findings: `Batch analysis complete. Highlighted document: ${criticalResult.filename}.`
        });
      }

      setSelectedFiles([]);
    } catch (error) {
      console.error("Batch upload failed:", error);
      setResults(prev => prev.map(r => r.status === "processing" ? { ...r, status: "error" } : r));
    } finally {
      setIsUploading(false);
    }
  };

  const total = results.length;
  const safeCount = results.filter(r => r.risk === "safe").length;
  const highRiskCount = results.filter(r => r.risk === "high").length;

  return (
    <div className="flex min-h-screen bg-[#0a0a0a] text-white selection:bg-[#00FF9C]/20">
      
      {/* Sidebar Navigation */}
      <aside className="w-24 flex-shrink-0 border-r border-white/5 flex flex-col items-center py-10 gap-10 bg-black/20 backdrop-blur-xl">
        <div className="bg-[#00FF9C] p-3 rounded-2xl shadow-[0_0_20px_rgba(0,255,156,0.3)]">
          <Shield className="w-6 h-6 text-black" />
        </div>
        
        <nav className="flex flex-col gap-8">
          <button className="p-3 text-[#00FF9C] bg-[#00FF9C]/10 rounded-xl transition-all"><LayoutDashboard className="w-6 h-6" /></button>
          <button className="p-3 text-white/20 hover:text-white transition-all"><History className="w-6 h-6" /></button>
          <button className="p-3 text-white/20 hover:text-white transition-all"><Bell className="w-6 h-6" /></button>
          <button className="p-3 text-white/20 hover:text-white transition-all"><Settings className="w-6 h-6" /></button>
        </nav>

        <div className="mt-auto">
          <button className="p-3 text-white/20 hover:text-rose-500 transition-all"><LogOut className="w-6 h-6" /></button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="max-w-7xl mx-auto px-10 py-12 space-y-12">
          
          {/* Header */}
          <header className="flex items-center justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <h1 className="text-4xl font-black tracking-tighter uppercase italic">
                  Kavach <span className="text-[#00FF9C]">AI</span>
                </h1>
                <div className="px-2 py-0.5 bg-white/5 border border-white/10 rounded text-[10px] font-black uppercase tracking-widest text-white/40">v2.0 PRO</div>
              </div>
              <p className="text-white/40 font-medium tracking-tight">Enterprise Document Forensic Pipeline</p>
            </div>

            <div className="flex items-center gap-4">
              <div className="relative hidden md:block">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20" />
                <input 
                  type="text" 
                  placeholder="Search repository..." 
                  className="pl-12 pr-6 py-3 bg-white/5 border border-white/5 rounded-2xl text-sm focus:outline-none focus:border-[#00FF9C]/30 transition-all w-64"
                />
              </div>
              <div className="flex items-center gap-2 px-4 py-2 bg-[#00FF9C]/5 rounded-full border border-[#00FF9C]/10">
                <Zap className="w-3.5 h-3.5 text-[#00FF9C] fill-[#00FF9C]" />
                <span className="text-[10px] font-black text-[#00FF9C] uppercase tracking-widest leading-none">System Live</span>
              </div>
            </div>
          </header>

          {/* Summary Section */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { label: "Analytic Load", value: total, icon: FileStack, color: "blue", sub: "Total documents processed" },
              { label: "Integrity Verified", value: safeCount, icon: ShieldCheck, color: "emerald", sub: "Clear of known exploits" },
              { label: "Threats Isolated", value: highRiskCount, icon: ShieldAlert, color: "rose", sub: "High-confidence forgeries" }
            ].map((stat, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                key={stat.label} 
                className="glass rounded-[2rem] p-8 group relative overflow-hidden"
              >
                <div className={`absolute top-0 right-0 w-32 h-32 bg-${stat.color}-500/10 blur-[60px] group-hover:bg-${stat.color}-500/20 transition-all`} />
                <div className="flex items-start justify-between relative z-10">
                  <div className="space-y-4">
                    <p className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">{stat.label}</p>
                    <p className="text-5xl font-black tracking-tighter">{stat.value}</p>
                    <p className="text-xs font-medium text-white/20">{stat.sub}</p>
                  </div>
                  <div className="p-4 bg-white/5 rounded-2xl border border-white/5 group-hover:border-white/10 transition-all">
                    <stat.icon className={`w-6 h-6 text-white/40 group-hover:text-white transition-colors`} />
                  </div>
                </div>
              </motion.div>
            ))}
          </section>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-10">
            {/* Primary Action Zone */}
            <aside className="xl:col-span-4">
              <div className="sticky top-12">
                <BatchUpload 
                  files={selectedFiles}
                  onFilesSelected={handleFilesSelected}
                  onRemoveFile={handleRemoveFile}
                  onUpload={handleUploadAll}
                  isUploading={isUploading}
                />
              </div>
            </aside>

            {/* Results Intelligence */}
            <section className="xl:col-span-8 space-y-6">
              <div className="flex items-center justify-between px-2">
                <h3 className="text-lg font-black uppercase tracking-widest text-white/60 italic">Intelligence Feed</h3>
                <div className="text-[10px] font-bold text-white/20 uppercase tracking-widest">Real-time updates</div>
              </div>
              <ResultsTable 
                results={results}
                onViewDetails={(id) => window.location.href = `/analysis/${id}`}
              />
            </section>
          </div>
        </div>
      </main>
      <ChatAssistant context={activeContext} />
    </div>
  );
}
