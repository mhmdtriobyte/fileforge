/**
 * DropZone.tsx - File Drop Zone Component
 *
 * Large centered drop area with drag-and-drop support using react-dropzone.
 * Features animated upload icon and visual feedback on drag hover.
 */

import React, { useCallback } from 'react';
import { useDropzone, FileRejection } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileUp, AlertCircle } from 'lucide-react';

interface DropZoneProps {
  onFilesAdded: (files: File[]) => void;
  disabled?: boolean;
  maxSize?: number; // in bytes
  maxFiles?: number;
}

const DropZone: React.FC<DropZoneProps> = ({
  onFilesAdded,
  disabled = false,
  maxSize = 100 * 1024 * 1024, // 100MB default
  maxFiles = 10,
}) => {
  const [error, setError] = React.useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError(`File is too large. Maximum size is ${formatBytes(maxSize)}.`);
        } else if (rejection.errors[0]?.code === 'too-many-files') {
          setError(`Too many files. Maximum is ${maxFiles} files at once.`);
        } else {
          setError(rejection.errors[0]?.message || 'File rejected');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onFilesAdded(acceptedFiles);
      }
    },
    [onFilesAdded, maxSize, maxFiles]
  );

  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragAccept,
    isDragReject,
  } = useDropzone({
    onDrop,
    disabled,
    maxSize,
    maxFiles,
    multiple: true,
  });

  // Format bytes to human readable
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Determine border and background colors based on state
  const getBorderColor = () => {
    if (disabled) return 'border-slate-700/30';
    if (isDragReject) return 'border-red-500/50';
    if (isDragAccept || isDragActive) return 'border-violet-500/70';
    return 'border-slate-700/50 hover:border-slate-600/70';
  };

  const getBackgroundColor = () => {
    if (disabled) return 'bg-slate-800/20';
    if (isDragReject) return 'bg-red-500/5';
    if (isDragAccept || isDragActive) return 'bg-violet-500/10';
    return 'bg-slate-800/30 hover:bg-slate-800/50';
  };

  return (
    <div className="w-full">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div
          {...getRootProps()}
          className={`
            relative overflow-hidden rounded-2xl border-2 border-dashed
            ${getBorderColor()}
            ${getBackgroundColor()}
            transition-all duration-300 ease-out
            ${disabled ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'}
          `}
        >
          <input {...getInputProps()} />

          {/* Gradient Overlay on Drag */}
          <AnimatePresence>
            {isDragActive && !isDragReject && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-gradient-to-br from-violet-500/10 to-blue-500/10 pointer-events-none"
              />
            )}
          </AnimatePresence>

          {/* Content */}
          <div className="relative py-16 px-8 flex flex-col items-center justify-center text-center">
            {/* Animated Icon */}
            <motion.div
              className="relative mb-6"
              animate={
                isDragActive
                  ? { scale: 1.1, y: -5 }
                  : { scale: 1, y: 0 }
              }
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              {/* Glow Effect */}
              <div
                className={`
                  absolute inset-0 rounded-full blur-2xl transition-all duration-300
                  ${isDragActive ? 'bg-violet-500/30 scale-150' : 'bg-violet-500/10 scale-100'}
                `}
              />

              {/* Icon Container */}
              <div
                className={`
                  relative p-5 rounded-2xl transition-all duration-300
                  ${isDragActive
                    ? 'bg-gradient-to-br from-violet-500 to-blue-500'
                    : 'bg-slate-800/80 border border-slate-700/50'
                  }
                `}
              >
                <AnimatePresence mode="wait">
                  {isDragActive ? (
                    <motion.div
                      key="active"
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{ scale: 1, rotate: 0 }}
                      exit={{ scale: 0, rotate: 180 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                    >
                      <FileUp className="w-10 h-10 text-white" />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="idle"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                    >
                      <Upload className="w-10 h-10 text-slate-400" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>

            {/* Text */}
            <motion.div
              animate={isDragActive ? { y: -3 } : { y: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            >
              <h3 className="text-lg font-semibold text-slate-200 mb-2">
                {isDragActive
                  ? isDragReject
                    ? 'File type not supported'
                    : 'Drop your files here'
                  : 'Drop files here or click to browse'}
              </h3>
              <p className="text-sm text-slate-500">
                Supports images, documents, audio, video and more
              </p>
              <p className="text-xs text-slate-600 mt-2">
                Maximum {maxFiles} files, up to {formatBytes(maxSize)} each
              </p>
            </motion.div>

            {/* Supported Formats Pills */}
            <div className="flex flex-wrap gap-2 mt-6 justify-center">
              {['PNG', 'JPG', 'PDF', 'DOCX', 'MP4', 'MP3'].map((format) => (
                <span
                  key={format}
                  className="px-3 py-1 text-xs font-medium text-slate-400 bg-slate-800/50 rounded-full border border-slate-700/30"
                >
                  {format}
                </span>
              ))}
            </div>
          </div>

          {/* Bottom Gradient Line */}
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />
        </div>
      </motion.div>

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="mt-3 flex items-center gap-2 text-red-400 text-sm"
          >
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DropZone;
