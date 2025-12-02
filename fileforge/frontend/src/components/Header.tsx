/**
 * Header.tsx - Application Header Component
 *
 * Displays the FileForge logo and provides theme toggle functionality.
 * Clean, modern design with smooth transitions.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Anvil, Sun, Moon } from 'lucide-react';

interface HeaderProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
}

const Header: React.FC<HeaderProps> = ({ theme, onToggleTheme }) => {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-slate-900/80 border-b border-slate-800/50">
      <div className="container mx-auto px-4 py-4 max-w-4xl">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Logo Icon with Gradient */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-violet-500 to-blue-500 rounded-xl blur-lg opacity-50" />
              <div className="relative bg-gradient-to-br from-violet-500 to-blue-500 p-2.5 rounded-xl">
                <Anvil className="w-6 h-6 text-white" strokeWidth={2.5} />
              </div>
            </div>

            {/* Logo Text */}
            <div className="flex flex-col">
              <h1 className="text-xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
                FileForge
              </h1>
              <span className="text-xs text-slate-500 -mt-0.5">
                File Converter
              </span>
            </div>
          </motion.div>

          {/* Theme Toggle */}
          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4 }}
            onClick={onToggleTheme}
            className="relative p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-slate-600/50 transition-all duration-200 group"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {/* Background Glow on Hover */}
            <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-violet-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-200" />

            {/* Icon Container */}
            <div className="relative w-5 h-5">
              {/* Sun Icon */}
              <motion.div
                initial={false}
                animate={{
                  scale: theme === 'light' ? 1 : 0,
                  opacity: theme === 'light' ? 1 : 0,
                  rotate: theme === 'light' ? 0 : -90,
                }}
                transition={{ duration: 0.2 }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <Sun className="w-5 h-5 text-amber-400" />
              </motion.div>

              {/* Moon Icon */}
              <motion.div
                initial={false}
                animate={{
                  scale: theme === 'dark' ? 1 : 0,
                  opacity: theme === 'dark' ? 1 : 0,
                  rotate: theme === 'dark' ? 0 : 90,
                }}
                transition={{ duration: 0.2 }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <Moon className="w-5 h-5 text-slate-300" />
              </motion.div>
            </div>
          </motion.button>
        </div>
      </div>
    </header>
  );
};

export default Header;
