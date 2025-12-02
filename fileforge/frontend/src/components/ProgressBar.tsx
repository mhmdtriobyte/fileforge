/**
 * ProgressBar.tsx - Animated Progress Bar Component
 *
 * Displays conversion progress with smooth animations,
 * percentage text, and visual transitions using framer-motion.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';

interface ProgressBarProps {
  progress: number; // 0-100
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  showLabel = true,
  size = 'md',
}) => {
  // Clamp progress between 0 and 100
  const clampedProgress = Math.min(100, Math.max(0, progress));

  // Size configurations
  const sizeConfig = {
    sm: {
      height: 'h-1.5',
      padding: 'p-4',
      text: 'text-sm',
    },
    md: {
      height: 'h-2.5',
      padding: 'p-6',
      text: 'text-base',
    },
    lg: {
      height: 'h-4',
      padding: 'p-8',
      text: 'text-lg',
    },
  };

  const config = sizeConfig[size];

  // Get status message based on progress
  const getStatusMessage = (): string => {
    if (clampedProgress < 25) return 'Uploading file...';
    if (clampedProgress < 50) return 'Preparing conversion...';
    if (clampedProgress < 75) return 'Converting...';
    if (clampedProgress < 100) return 'Finalizing...';
    return 'Complete!';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={`${config.padding} bg-slate-800/50 rounded-xl border border-slate-700/50`}
    >
      {/* Header */}
      {showLabel && (
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            >
              <Zap className="w-4 h-4 text-violet-400" />
            </motion.div>
            <span className="text-sm font-medium text-slate-300">
              {getStatusMessage()}
            </span>
          </div>
          <motion.span
            key={Math.floor(clampedProgress)}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className={`${config.text} font-bold bg-gradient-to-r from-violet-400 to-blue-400 bg-clip-text text-transparent`}
          >
            {Math.round(clampedProgress)}%
          </motion.span>
        </div>
      )}

      {/* Progress Bar Container */}
      <div className={`relative ${config.height} bg-slate-700/50 rounded-full overflow-hidden`}>
        {/* Background Pattern */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 10px, rgba(255,255,255,0.03) 10px, rgba(255,255,255,0.03) 20px)',
          }}
        />

        {/* Progress Fill */}
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-violet-500 via-violet-400 to-blue-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${clampedProgress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        >
          {/* Animated Shine */}
          <motion.div
            className="absolute inset-0"
            animate={{
              backgroundPosition: ['200% 0', '-200% 0'],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'linear',
            }}
            style={{
              background: 'linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.3) 50%, transparent 100%)',
              backgroundSize: '50% 100%',
            }}
          />

          {/* Glow Effect */}
          <div className="absolute right-0 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full blur-md opacity-60" />
        </motion.div>

        {/* Pulse Animation at Current Position */}
        {clampedProgress > 0 && clampedProgress < 100 && (
          <motion.div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full"
            style={{ left: `calc(${clampedProgress}% - 6px)` }}
            animate={{
              scale: [1, 1.5, 1],
              opacity: [0.8, 0.4, 0.8],
            }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </div>

      {/* Progress Steps */}
      {showLabel && (
        <div className="flex justify-between mt-3">
          {['Upload', 'Process', 'Convert', 'Complete'].map((step, index) => {
            const stepProgress = (index / 3) * 100;
            const isActive = clampedProgress >= stepProgress;
            const isCurrent =
              clampedProgress >= stepProgress &&
              clampedProgress < ((index + 1) / 3) * 100;

            return (
              <motion.div
                key={step}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: index * 0.1 }}
                className="flex flex-col items-center"
              >
                <motion.div
                  className={`w-2 h-2 rounded-full mb-1 ${
                    isActive
                      ? 'bg-gradient-to-r from-violet-500 to-blue-500'
                      : 'bg-slate-600'
                  }`}
                  animate={
                    isCurrent
                      ? {
                          scale: [1, 1.3, 1],
                        }
                      : {}
                  }
                  transition={{
                    duration: 0.8,
                    repeat: isCurrent ? Infinity : 0,
                    ease: 'easeInOut',
                  }}
                />
                <span
                  className={`text-xs ${
                    isActive ? 'text-slate-300' : 'text-slate-600'
                  }`}
                >
                  {step}
                </span>
              </motion.div>
            );
          })}
        </div>
      )}
    </motion.div>
  );
};

export default ProgressBar;
