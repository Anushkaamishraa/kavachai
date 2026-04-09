
"use client";

import React from "react";
import { CheckCircle, AlertTriangle, XCircle, Loader2, ArrowRight, ShieldCheck, ShieldAlert, Shield } from "lucide-react";
import { motion } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export interface AnalysisResult {
  file_id: string;
  filename: string;
  trust_score: number;
  risk: "safe" | "medium" | "high";
  status: "pending" | "processing" | "completed" | "error";
}

interface ResultsTableProps {
  results: AnalysisResult[];
  onViewDetails: (fileId: string) => void;
}

export default function ResultsTable({ results, onViewDetails }: ResultsTableProps) {
  const getRiskBadge = (risk: string) => {
    switch (risk) {
      case "safe":
        return (
          <div className="flex items-center gap-2 text-[#00FF9C] bg-[#00FF9C]/10 px-3 py-1 rounded-full border border-[#00FF9C]/20 shadow-[0_0_15px_rgba(0,255,156,0.1)]">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span className="text-[10px] font-black uppercase tracking-widest">Safe</span>
          </div>
        );
      case "medium":
        return (
          <div className="flex items-center gap-2 text-amber-400 bg-amber-400/10 px-3 py-1 rounded-full border border-amber-400/20">
            <Shield className="w-3.5 h-3.5" />
            <span className="text-[10px] font-black uppercase tracking-widest">Caution</span>
          </div>
        );
      case "high":
        return (
          <div className="flex items-center gap-2 text-rose-500 bg-rose-500/10 px-3 py-1 rounded-full border border-rose-500/20 shadow-[0_0_15px_rgba(244,63,94,0.1)]">
            <ShieldAlert className="w-3.5 h-3.5" />
            <span className="text-[10px] font-black uppercase tracking-widest">Threat</span>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="glass rounded-3xl overflow-hidden border border-white/5 relative group">
      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-white/[0.02] border-b border-white/5">
              <th className="px-8 py-6 text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">Document</th>
              <th className="px-8 py-6 text-[10px] font-black text-white/30 uppercase tracking-[0.2em] text-center">Trust Integrity</th>
              <th className="px-8 py-6 text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">Risk Status</th>
              <th className="px-8 py-6 text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">Operational State</th>
              <th className="px-8 py-6 text-[10px] font-black text-white/30 uppercase tracking-[0.2em] text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {results.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-8 py-32 text-center">
                  <div className="flex flex-col items-center gap-4">
                    <div className="p-6 bg-white/[0.02] rounded-full border border-white/5 animate-pulse">
                      <Shield className="w-12 h-12 text-white/10" />
                    </div>
                    <p className="text-sm font-bold text-white/20 italic tracking-tight">System idle. Awaiting document ingestion.</p>
                  </div>
                </td>
              </tr>
            ) : (
              results.map((result, i) => (
                <motion.tr 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  key={result.file_id} 
                  className={cn(
                    "group/row hover:bg-white/[0.02] transition-colors relative",
                    result.risk === "high" && "bg-rose-500/[0.02]"
                  )}
                >
                  <td className="px-8 py-6">
                    <div className="flex flex-col gap-1">
                      <span className="text-sm font-bold text-white/90 group-hover/row:text-[#00FF9C] transition-colors truncate max-w-[220px] tracking-tight">{result.filename}</span>
                      <span className="text-[10px] font-mono text-white/20 uppercase tracking-tighter">HEX: {result.file_id.slice(0, 12)}</span>
                    </div>
                  </td>
                  
                  <td className="px-8 py-6">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-24 h-1.5 bg-white/[0.05] rounded-full overflow-hidden border border-white/5">
                        <motion.div 
                          initial={{ width: 0 }}
                          animate={{ width: `${result.trust_score}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                          className={cn(
                            "h-full rounded-full shadow-[0_0_10px_rgba(0,255,156,0.3)]",
                            result.trust_score >= 80 ? "bg-[#00FF9C]" : result.trust_score >= 50 ? "bg-amber-400" : "bg-rose-500"
                          )} 
                        />
                      </div>
                      <span className="text-xs font-black text-white/60">{result.trust_score}%</span>
                    </div>
                  </td>

                  <td className="px-8 py-6">
                    <div className="inline-block transition-transform group-hover/row:scale-105 duration-300">
                      {result.status === "completed" ? getRiskBadge(result.risk) : <div className="w-20 h-6 bg-white/5 rounded-full animate-pulse" />}
                    </div>
                  </td>

                  <td className="px-8 py-6">
                    {result.status === "processing" ? (
                      <div className="flex items-center gap-3 text-blue-400">
                        <div className="relative">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <div className="absolute inset-0 blur-md bg-blue-400/30 animate-pulse" />
                        </div>
                        <span className="text-[10px] font-black uppercase tracking-[0.15em]">Analyzing...</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3 text-[#00FF9C]/60">
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-[10px] font-black uppercase tracking-[0.15em]">Verified</span>
                      </div>
                    )}
                  </td>

                  <td className="px-8 py-6 text-right">
                    <button 
                      onClick={() => onViewDetails(result.file_id)}
                      disabled={result.status !== "completed"}
                      className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-[#00FF9C]/60 hover:text-[#00FF9C] disabled:opacity-10 transition-all group/btn"
                    >
                      Report
                      <ArrowRight className="w-3 h-3 transition-transform group-hover/btn:translate-x-1" />
                    </button>
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
