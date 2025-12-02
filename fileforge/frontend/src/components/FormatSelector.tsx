/**
 * FormatSelector.tsx - Output Format Selection Component
 *
 * Provides dropdown to select output format based on input file type.
 * Includes quality slider for image conversions.
 */

import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown, Settings2 } from 'lucide-react';

interface FormatSelectorProps {
  inputType: string;
  selectedFormat: string;
  onFormatChange: (format: string) => void;
  quality: number;
  onQualityChange: (quality: number) => void;
  availableFormats: Record<string, string[]>;
  disabled?: boolean;
}

// Default format mappings when API formats not available
const DEFAULT_FORMAT_MAP: Record<string, string[]> = {
  // Images
  png: ['jpg', 'jpeg', 'webp', 'gif', 'bmp', 'ico', 'pdf'],
  jpg: ['png', 'webp', 'gif', 'bmp', 'ico', 'pdf'],
  jpeg: ['png', 'webp', 'gif', 'bmp', 'ico', 'pdf'],
  webp: ['png', 'jpg', 'gif', 'bmp', 'pdf'],
  gif: ['png', 'jpg', 'webp', 'mp4'],
  bmp: ['png', 'jpg', 'webp', 'gif'],
  svg: ['png', 'jpg', 'webp', 'pdf'],
  ico: ['png', 'jpg'],

  // Documents
  pdf: ['docx', 'txt', 'png', 'jpg'],
  doc: ['pdf', 'docx', 'txt', 'rtf'],
  docx: ['pdf', 'doc', 'txt', 'rtf'],
  txt: ['pdf', 'docx', 'rtf'],
  rtf: ['pdf', 'docx', 'txt'],

  // Audio
  mp3: ['wav', 'ogg', 'flac', 'aac', 'm4a'],
  wav: ['mp3', 'ogg', 'flac', 'aac'],
  ogg: ['mp3', 'wav', 'flac', 'aac'],
  flac: ['mp3', 'wav', 'ogg', 'aac'],
  aac: ['mp3', 'wav', 'ogg', 'flac'],
  m4a: ['mp3', 'wav', 'ogg', 'flac'],

  // Video
  mp4: ['webm', 'avi', 'mkv', 'mov', 'gif'],
  webm: ['mp4', 'avi', 'mkv', 'mov', 'gif'],
  avi: ['mp4', 'webm', 'mkv', 'mov'],
  mkv: ['mp4', 'webm', 'avi', 'mov'],
  mov: ['mp4', 'webm', 'avi', 'mkv', 'gif'],

  // Spreadsheets
  xlsx: ['csv', 'pdf', 'xls'],
  xls: ['csv', 'pdf', 'xlsx'],
  csv: ['xlsx', 'xls', 'pdf'],

  // Presentations
  pptx: ['pdf', 'ppt'],
  ppt: ['pdf', 'pptx'],
};

// Image formats that support quality adjustment
const IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp'];

const FormatSelector: React.FC<FormatSelectorProps> = ({
  inputType,
  selectedFormat,
  onFormatChange,
  quality,
  onQualityChange,
  availableFormats,
  disabled = false,
}) => {
  // Get available output formats based on input type
  const outputFormats = useMemo(() => {
    const normalizedInput = inputType.toLowerCase();

    // Try API formats first, then fall back to defaults
    if (availableFormats && availableFormats[normalizedInput]) {
      return availableFormats[normalizedInput];
    }

    return DEFAULT_FORMAT_MAP[normalizedInput] || [];
  }, [inputType, availableFormats]);

  // Check if quality slider should be shown
  const showQualitySlider = useMemo(() => {
    return IMAGE_FORMATS.includes(selectedFormat.toLowerCase());
  }, [selectedFormat]);

  // Get format category for styling
  const getFormatCategory = (format: string): string => {
    const f = format.toLowerCase();
    if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp', 'svg', 'ico'].includes(f)) return 'image';
    if (['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'].includes(f)) return 'audio';
    if (['mp4', 'webm', 'avi', 'mkv', 'mov'].includes(f)) return 'video';
    if (['pdf', 'doc', 'docx', 'txt', 'rtf'].includes(f)) return 'document';
    return 'other';
  };

  // Get color for format badge
  const getCategoryColor = (category: string): string => {
    switch (category) {
      case 'image':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'audio':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      case 'video':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      case 'document':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  if (outputFormats.length === 0) {
    return (
      <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700/50">
        <p className="text-sm text-slate-500">
          No conversion formats available for this file type.
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 bg-slate-800/50 rounded-xl border border-slate-700/50"
    >
      {/* Format Selection */}
      <div className="space-y-3">
        <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
          <Settings2 className="w-4 h-4 text-slate-500" />
          Convert to
        </label>

        <div className="relative">
          <select
            value={selectedFormat}
            onChange={(e) => onFormatChange(e.target.value)}
            disabled={disabled}
            className={`
              w-full appearance-none px-4 py-3 pr-10 rounded-xl
              bg-slate-900/50 border border-slate-700/50
              text-slate-200 text-sm font-medium uppercase tracking-wider
              transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500/50
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-slate-600/50 cursor-pointer'}
            `}
          >
            <option value="" disabled className="text-slate-500">
              Select output format...
            </option>
            {outputFormats.map((format) => (
              <option
                key={format}
                value={format}
                className="bg-slate-800 text-slate-200 py-2"
              >
                {format.toUpperCase()}
              </option>
            ))}
          </select>

          {/* Dropdown Arrow */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <ChevronDown className="w-5 h-5 text-slate-500" />
          </div>
        </div>

        {/* Format Pills (alternative selection method) */}
        <div className="flex flex-wrap gap-2 mt-4">
          {outputFormats.slice(0, 6).map((format) => {
            const category = getFormatCategory(format);
            const isSelected = selectedFormat === format;

            return (
              <motion.button
                key={format}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => !disabled && onFormatChange(format)}
                disabled={disabled}
                className={`
                  px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wider
                  border transition-all duration-200
                  ${isSelected
                    ? 'bg-gradient-to-r from-violet-500 to-blue-500 text-white border-transparent'
                    : `${getCategoryColor(category)} hover:brightness-110`
                  }
                  ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                {format}
              </motion.button>
            );
          })}
          {outputFormats.length > 6 && (
            <span className="px-3 py-2 text-xs text-slate-500">
              +{outputFormats.length - 6} more in dropdown
            </span>
          )}
        </div>
      </div>

      {/* Quality Slider (for images) */}
      {showQualitySlider && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-6 pt-6 border-t border-slate-700/50"
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-slate-300">
                Quality
              </label>
              <span className="text-sm font-semibold text-violet-400">
                {quality}%
              </span>
            </div>

            {/* Custom Slider */}
            <div className="relative h-6 flex items-center">
              {/* Track background */}
              <div className="absolute w-full h-2 rounded-full bg-slate-700/50" />

              {/* Track fill */}
              <div
                className="absolute h-2 rounded-full bg-gradient-to-r from-violet-500 to-blue-500 pointer-events-none"
                style={{ width: `${quality}%` }}
              />

              {/* Slider input */}
              <input
                type="range"
                min="1"
                max="100"
                value={quality}
                onChange={(e) => onQualityChange(parseInt(e.target.value, 10))}
                disabled={disabled}
                className={`
                  relative w-full h-2 rounded-full appearance-none cursor-pointer
                  bg-transparent
                  [&::-webkit-slider-thumb]:appearance-none
                  [&::-webkit-slider-thumb]:w-5
                  [&::-webkit-slider-thumb]:h-5
                  [&::-webkit-slider-thumb]:rounded-full
                  [&::-webkit-slider-thumb]:bg-gradient-to-r
                  [&::-webkit-slider-thumb]:from-violet-500
                  [&::-webkit-slider-thumb]:to-blue-500
                  [&::-webkit-slider-thumb]:shadow-lg
                  [&::-webkit-slider-thumb]:shadow-violet-500/30
                  [&::-webkit-slider-thumb]:transition-transform
                  [&::-webkit-slider-thumb]:hover:scale-110
                  [&::-webkit-slider-thumb]:cursor-pointer
                  [&::-webkit-slider-thumb]:border-2
                  [&::-webkit-slider-thumb]:border-white/20
                  [&::-moz-range-thumb]:w-5
                  [&::-moz-range-thumb]:h-5
                  [&::-moz-range-thumb]:rounded-full
                  [&::-moz-range-thumb]:bg-gradient-to-r
                  [&::-moz-range-thumb]:from-violet-500
                  [&::-moz-range-thumb]:to-blue-500
                  [&::-moz-range-thumb]:border-2
                  [&::-moz-range-thumb]:border-white/20
                  [&::-moz-range-thumb]:cursor-pointer
                  [&::-webkit-slider-runnable-track]:bg-transparent
                  [&::-moz-range-track]:bg-transparent
                  ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              />
            </div>

            {/* Quality Labels */}
            <div className="flex justify-between text-xs text-slate-500">
              <span>Smaller file</span>
              <span>Best quality</span>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  );
};

export default FormatSelector;
