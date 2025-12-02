/**
 * FileCard.tsx - File Display Card Component
 *
 * Displays file information including name, size, and type icon.
 * Features a remove button and clean card design.
 */

import React from 'react';
import { motion } from 'framer-motion';
import {
  X,
  Image,
  FileText,
  FileAudio,
  FileVideo,
  File,
  FileArchive,
  FileSpreadsheet,
  Presentation,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import type { FileItem } from '../App';

interface FileCardProps {
  file: FileItem;
  onRemove: () => void;
  disabled?: boolean;
}

const FileCard: React.FC<FileCardProps> = ({ file, onRemove, disabled = false }) => {
  // Format file size to human readable
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

  // Get icon based on file type
  const getFileIcon = () => {
    const ext = getExtension(file.name);
    const mimeType = file.type.split('/')[0];

    // Image files
    if (mimeType === 'image' || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) {
      return <Image className="w-5 h-5" />;
    }

    // Audio files
    if (mimeType === 'audio' || ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'].includes(ext)) {
      return <FileAudio className="w-5 h-5" />;
    }

    // Video files
    if (mimeType === 'video' || ['mp4', 'avi', 'mkv', 'mov', 'webm', 'wmv'].includes(ext)) {
      return <FileVideo className="w-5 h-5" />;
    }

    // Document files
    if (['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt'].includes(ext)) {
      return <FileText className="w-5 h-5" />;
    }

    // Spreadsheet files
    if (['xls', 'xlsx', 'csv', 'ods'].includes(ext)) {
      return <FileSpreadsheet className="w-5 h-5" />;
    }

    // Presentation files
    if (['ppt', 'pptx', 'odp'].includes(ext)) {
      return <Presentation className="w-5 h-5" />;
    }

    // Archive files
    if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
      return <FileArchive className="w-5 h-5" />;
    }

    // Default file icon
    return <File className="w-5 h-5" />;
  };

  // Get icon color based on file type
  const getIconColor = (): string => {
    const ext = getExtension(file.name);
    const mimeType = file.type.split('/')[0];

    if (mimeType === 'image' || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) {
      return 'text-emerald-400';
    }
    if (mimeType === 'audio' || ['mp3', 'wav', 'ogg', 'flac'].includes(ext)) {
      return 'text-amber-400';
    }
    if (mimeType === 'video' || ['mp4', 'avi', 'mkv', 'mov', 'webm'].includes(ext)) {
      return 'text-rose-400';
    }
    if (['pdf', 'doc', 'docx'].includes(ext)) {
      return 'text-blue-400';
    }
    if (['xls', 'xlsx', 'csv'].includes(ext)) {
      return 'text-green-400';
    }
    if (['ppt', 'pptx'].includes(ext)) {
      return 'text-orange-400';
    }
    if (['zip', 'rar', '7z'].includes(ext)) {
      return 'text-purple-400';
    }

    return 'text-slate-400';
  };

  // Get status indicator
  const getStatusIndicator = () => {
    switch (file.status) {
      case 'uploading':
      case 'converting':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            <Loader2 className="w-4 h-4 text-violet-400" />
          </motion.div>
        );
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  // Get status text
  const getStatusText = (): string => {
    switch (file.status) {
      case 'uploading':
        return 'Uploading...';
      case 'uploaded':
        return 'Uploaded';
      case 'converting':
        return 'Converting...';
      case 'completed':
        return 'Completed';
      case 'error':
        return file.error || 'Error';
      default:
        return 'Ready';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.98 }}
      transition={{ duration: 0.2 }}
      className={`
        relative group rounded-xl border transition-all duration-200
        ${file.status === 'error'
          ? 'bg-red-500/5 border-red-500/20'
          : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600/50'
        }
      `}
    >
      <div className="p-4 flex items-center gap-4">
        {/* File Type Icon */}
        <div
          className={`
            flex-shrink-0 p-3 rounded-xl transition-colors duration-200
            ${file.status === 'error' ? 'bg-red-500/10' : 'bg-slate-700/50'}
          `}
        >
          <span className={getIconColor()}>{getFileIcon()}</span>
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium text-slate-200 truncate">
              {file.name}
            </h4>
            {getStatusIndicator()}
          </div>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-slate-500">{formatSize(file.size)}</span>
            <span className="text-xs text-slate-600">|</span>
            <span className="text-xs text-slate-500 uppercase">
              {getExtension(file.name)}
            </span>
            {file.status !== 'pending' && (
              <>
                <span className="text-xs text-slate-600">|</span>
                <span
                  className={`text-xs ${
                    file.status === 'error'
                      ? 'text-red-400'
                      : file.status === 'completed'
                      ? 'text-emerald-400'
                      : 'text-slate-400'
                  }`}
                >
                  {getStatusText()}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Progress Indicator (when uploading/converting) */}
        {(file.status === 'uploading' || file.status === 'converting') && (
          <div className="flex-shrink-0 w-16">
            <div className="text-right text-xs font-medium text-violet-400">
              {Math.round(file.progress)}%
            </div>
          </div>
        )}

        {/* Remove Button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onRemove}
          disabled={disabled}
          className={`
            flex-shrink-0 p-2 rounded-lg transition-all duration-200
            ${disabled
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:bg-slate-700/50 text-slate-500 hover:text-slate-300'
            }
          `}
          aria-label="Remove file"
        >
          <X className="w-4 h-4" />
        </motion.button>
      </div>

      {/* Progress Bar (at bottom of card) */}
      {(file.status === 'uploading' || file.status === 'converting') && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-700/50 rounded-b-xl overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-violet-500 to-blue-500"
            initial={{ width: 0 }}
            animate={{ width: `${file.progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      )}
    </motion.div>
  );
};

export default FileCard;
