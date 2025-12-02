/**
 * DownloadCard.tsx - Download Success Card Component
 *
 * Displays successful conversion result with animated checkmark,
 * file information, and download/convert another buttons.
 */

import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircle2,
  Download,
  RefreshCw,
  FileCheck,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import type { FileItem } from '../App';

interface DownloadCardProps {
  file: FileItem;
  onDownload: () => void;
  onConvertAnother: () => void;
}

const DownloadCard: React.FC<DownloadCardProps> = ({
  file,
  onDownload,
  onConvertAnother,
}) => {
  const [showConfetti, setShowConfetti] = useState(true);

  // Hide confetti after animation
  useEffect(() => {
    const timer = setTimeout(() => setShowConfetti(false), 3000);
    return () => clearTimeout(timer);
  }, []);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get file extension
  const getExtension = (filename: string): string => {
    return filename.split('.').pop()?.toLowerCase() || '';
  };

  // Calculate size reduction
  const getSizeReduction = (): number | null => {
    if (!file.convertedSize || file.convertedSize >= file.size) return null;
    return Math.round((1 - file.convertedSize / file.size) * 100);
  };

  const sizeReduction = getSizeReduction();
  const inputExt = getExtension(file.name);
  const outputExt = file.outputFormat || 'file';

  // Generate output filename
  const outputFilename = file.name.replace(
    new RegExp(`\\.${inputExt}$`, 'i'),
    `.${outputExt}`
  );

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/50"
    >
      {/* Confetti Animation */}
      <AnimatePresence>
        {showConfetti && (
          <>
            {[...Array(12)].map((_, i) => (
              <motion.div
                key={i}
                initial={{
                  opacity: 1,
                  x: '50%',
                  y: '0%',
                  scale: 0,
                }}
                animate={{
                  opacity: 0,
                  x: `${50 + (Math.random() - 0.5) * 100}%`,
                  y: `${-50 - Math.random() * 100}%`,
                  scale: 1,
                  rotate: Math.random() * 360,
                }}
                exit={{ opacity: 0 }}
                transition={{
                  duration: 1.5 + Math.random(),
                  delay: Math.random() * 0.3,
                  ease: 'easeOut',
                }}
                className={`absolute w-2 h-2 rounded-full ${
                  ['bg-violet-400', 'bg-blue-400', 'bg-emerald-400', 'bg-amber-400'][
                    i % 4
                  ]
                }`}
              />
            ))}
          </>
        )}
      </AnimatePresence>

      {/* Success Header */}
      <div className="relative p-6 pb-4 text-center">
        {/* Glow Effect */}
        <div className="absolute inset-0 bg-gradient-to-b from-emerald-500/10 to-transparent" />

        {/* Animated Checkmark */}
        <motion.div
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{
            type: 'spring',
            stiffness: 260,
            damping: 20,
            delay: 0.1,
          }}
          className="relative mx-auto mb-4"
        >
          {/* Pulsing Ring */}
          <motion.div
            className="absolute inset-0 rounded-full bg-emerald-500/20"
            animate={{
              scale: [1, 1.5, 1],
              opacity: [0.5, 0, 0.5],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />

          {/* Icon Container */}
          <div className="relative w-16 h-16 mx-auto rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
            <motion.div
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <CheckCircle2 className="w-8 h-8 text-white" strokeWidth={2.5} />
            </motion.div>
          </div>
        </motion.div>

        {/* Success Text */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <h3 className="text-xl font-bold text-white mb-1">
            Conversion Complete!
          </h3>
          <p className="text-sm text-slate-400">
            Your file is ready for download
          </p>
        </motion.div>
      </div>

      {/* File Info */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mx-6 p-4 bg-slate-900/50 rounded-xl border border-slate-700/30"
      >
        <div className="flex items-center gap-4">
          {/* File Icon */}
          <div className="flex-shrink-0 p-3 rounded-xl bg-gradient-to-br from-violet-500/20 to-blue-500/20 border border-violet-500/20">
            <FileCheck className="w-6 h-6 text-violet-400" />
          </div>

          {/* File Details */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-200 truncate">
              {outputFilename}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-slate-500">
                {formatSize(file.convertedSize || file.size)}
              </span>
              {sizeReduction && (
                <>
                  <span className="text-xs text-slate-600">|</span>
                  <span className="text-xs text-emerald-400 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    {sizeReduction}% smaller
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Format Badge */}
          <div className="flex-shrink-0">
            <div className="flex items-center gap-2 text-xs">
              <span className="px-2 py-1 bg-slate-700/50 rounded text-slate-400 uppercase font-medium">
                {inputExt}
              </span>
              <ArrowRight className="w-3 h-3 text-slate-600" />
              <span className="px-2 py-1 bg-gradient-to-r from-violet-500/20 to-blue-500/20 rounded text-violet-300 uppercase font-medium border border-violet-500/20">
                {outputExt}
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="p-6 pt-4 flex gap-3"
      >
        {/* Download Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onDownload}
          className="flex-1 relative group overflow-hidden rounded-xl py-3.5 px-6 bg-gradient-to-r from-violet-600 to-blue-500 text-white font-semibold transition-all duration-300 hover:shadow-lg hover:shadow-violet-500/25"
        >
          {/* Shimmer */}
          <motion.div
            className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"
            style={{
              background:
                'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
            }}
          />

          <span className="relative flex items-center justify-center gap-2">
            <Download className="w-5 h-5" />
            Download
          </span>
        </motion.button>

        {/* Convert Another Button */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onConvertAnother}
          className="flex-shrink-0 rounded-xl py-3.5 px-5 bg-slate-700/50 border border-slate-600/50 text-slate-300 font-medium hover:bg-slate-700/70 hover:text-white transition-all duration-200"
        >
          <RefreshCw className="w-5 h-5" />
        </motion.button>
      </motion.div>

      {/* Bottom Gradient Line */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-violet-500/50 to-transparent" />
    </motion.div>
  );
};

export default DownloadCard;
