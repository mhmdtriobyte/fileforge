/**
 * ConvertButton.tsx - Conversion Action Button Component
 *
 * Large gradient button with hover animation, loading state,
 * and disabled state handling.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Loader2, ArrowRight } from 'lucide-react';

interface ConvertButtonProps {
  onClick: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  fileCount?: number;
}

const ConvertButton: React.FC<ConvertButtonProps> = ({
  onClick,
  disabled = false,
  isLoading = false,
  fileCount = 0,
}) => {
  const buttonText = isLoading
    ? 'Converting...'
    : fileCount > 1
    ? `Convert ${fileCount} Files`
    : 'Convert File';

  return (
    <motion.button
      onClick={onClick}
      disabled={disabled || isLoading}
      whileHover={!disabled && !isLoading ? { scale: 1.02 } : {}}
      whileTap={!disabled && !isLoading ? { scale: 0.98 } : {}}
      className={`
        relative w-full group overflow-hidden
        rounded-2xl py-4 px-8
        font-semibold text-base tracking-wide
        transition-all duration-300
        focus:outline-none focus:ring-4 focus:ring-violet-500/30
        ${disabled || isLoading
          ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
          : 'bg-gradient-to-r from-violet-600 via-violet-500 to-blue-500 text-white cursor-pointer hover:shadow-xl hover:shadow-violet-500/25'
        }
      `}
    >
      {/* Animated Background Gradient */}
      {!disabled && !isLoading && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-violet-500 via-blue-500 to-violet-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          animate={{
            backgroundPosition: ['0% 50%', '100% 50%', '0% 50%'],
          }}
          transition={{
            duration: 3,
            repeat: Infinity,
            ease: 'linear',
          }}
          style={{
            backgroundSize: '200% 200%',
          }}
        />
      )}

      {/* Shimmer Effect */}
      {!disabled && !isLoading && (
        <motion.div
          className="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)',
          }}
        />
      )}

      {/* Button Content */}
      <span className="relative flex items-center justify-center gap-3">
        {isLoading ? (
          <>
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            >
              <Loader2 className="w-5 h-5" />
            </motion.div>
            <span>{buttonText}</span>
          </>
        ) : (
          <>
            <Sparkles className="w-5 h-5" />
            <span>{buttonText}</span>
            <motion.div
              className="opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300"
            >
              <ArrowRight className="w-5 h-5" />
            </motion.div>
          </>
        )}
      </span>

      {/* Pulse Ring Animation (when enabled) */}
      {!disabled && !isLoading && (
        <motion.div
          className="absolute inset-0 rounded-2xl border-2 border-violet-400/30"
          animate={{
            scale: [1, 1.02, 1],
            opacity: [0.5, 0, 0.5],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}

      {/* Bottom Glow */}
      {!disabled && !isLoading && (
        <div className="absolute -bottom-4 left-1/4 right-1/4 h-8 bg-gradient-to-r from-violet-500 to-blue-500 blur-2xl opacity-50 group-hover:opacity-70 transition-opacity" />
      )}
    </motion.button>
  );
};

export default ConvertButton;
