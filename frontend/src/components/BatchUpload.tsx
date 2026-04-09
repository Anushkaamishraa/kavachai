
"use client";

import React, { useState, useRef } from "react";
import { Upload, File, X, Loader2, FileText, CheckCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface BatchUploadProps {
  onFilesSelected: (files: File[]) => void;
  onUpload: () => void;
  isUploading: boolean;
  files: File[];
  onRemoveFile: (index: number) => void;
}

export default function BatchUpload({
  onFilesSelected,
  onUpload,
  isUploading,
  files,
  onRemoveFile,
}: BatchUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files).filter(f => 
      ['image/jpeg', 'image/png', 'application/pdf'].includes(f.type) && f.size <= 10 * 1024 * 1024
    );
    onFilesSelected(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter(f => 
        ['image/jpeg', 'image/png', 'application/pdf'].includes(f.type) && f.size <= 10 * 1024 * 1024
      );
      onFilesSelected(selectedFiles);
    }
  };

  return (
    <div className="glass rounded-3xl p-8 space-y-8 relative overflow-hidden group">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-[#00FF9C] to-transparent opacity-30" />
      
      <motion.div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        className={cn(
          "relative border-2 border-dashed rounded-2xl p-12 transition-all flex flex-col items-center justify-center gap-5 cursor-pointer group/box",
          isDragging 
            ? "border-[#00FF9C] bg-[#00FF9C]/5 shadow-[0_0_30px_rgba(0,255,156,0.1)]" 
            : "border-white/10 hover:border-white/20 bg-white/[0.02]"
        )}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          multiple
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          accept=".jpg,.jpeg,.png,.pdf"
        />
        
        <div className="relative">
          <div className="absolute inset-0 bg-[#00FF9C] blur-2xl opacity-20 group-hover/box:opacity-40 transition-opacity" />
          <div className="relative bg-black/40 p-5 rounded-2xl border border-white/10 shadow-2xl">
            <Upload className="w-8 h-8 text-[#00FF9C]" />
          </div>
        </div>

        <div className="text-center space-y-2">
          <h3 className="text-xl font-bold text-white tracking-tight">Upload Documents</h3>
          <p className="text-sm text-white/40 font-medium">Drag & drop or click to browse</p>
          <div className="flex gap-2 justify-center pt-2">
            {['JPG', 'PNG', 'PDF'].map(ext => (
              <span key={ext} className="text-[10px] font-black px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/30 tracking-widest">{ext}</span>
            ))}
          </div>
        </div>
      </motion.div>

      <AnimatePresence>
        {files.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em]">Queue ({files.length})</p>
              <button onClick={() => onFilesSelected([])} className="text-[10px] font-black text-[#00FF9C]/60 hover:text-[#00FF9C] uppercase tracking-widest transition-colors">Clear All</button>
            </div>

            <div className="max-h-[280px] overflow-y-auto space-y-3 pr-2 custom-scrollbar">
              {files.map((file, idx) => (
                <motion.div 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={`${file.name}-${idx}`} 
                  className="flex items-center justify-between p-4 bg-white/[0.03] border border-white/5 rounded-2xl hover:bg-white/[0.05] transition-colors group/item"
                >
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-black/40 rounded-xl border border-white/10 group-hover/item:border-[#00FF9C]/30 transition-colors">
                      <FileText className="w-4 h-4 text-[#00FF9C]" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-white/80 truncate max-w-[160px] tracking-tight">{file.name}</p>
                      <p className="text-[10px] text-white/30 font-mono">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); onRemoveFile(idx); }} className="p-2 hover:bg-red-500/10 rounded-lg transition-colors group/del">
                    <X className="w-4 h-4 text-white/20 group-hover/del:text-red-400" />
                  </button>
                </motion.div>
              ))}
            </div>

            <motion.button
              whileHover={{ scale: 1.02, boxShadow: "0 0 30px rgba(0, 255, 156, 0.2)" }}
              whileTap={{ scale: 0.98 }}
              onClick={onUpload}
              disabled={isUploading}
              className="w-full py-5 bg-[#00FF9C] hover:bg-[#00FF9C]/90 disabled:bg-white/5 disabled:text-white/20 text-black font-black uppercase tracking-[0.15em] rounded-2xl transition-all flex items-center justify-center gap-3 relative overflow-hidden group/btn"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
              <span className="relative">
                {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Initiate Analysis"}
              </span>
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
