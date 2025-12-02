/**
 * App.tsx - Main Application Component
 *
 * Central component managing theme, file state, conversion process,
 * and overall application layout.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import Header from './components/Header';
import DropZone from './components/DropZone';
import FileCard from './components/FileCard';
import FormatSelector from './components/FormatSelector';
import ConvertButton from './components/ConvertButton';
import ProgressBar from './components/ProgressBar';
import DownloadCard from './components/DownloadCard';
import { useFileConvert } from './hooks/useFileConvert';

// Type definitions
export interface FileItem {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  uploadedId?: string;
  convertedId?: string;
  status: 'pending' | 'uploading' | 'uploaded' | 'converting' | 'completed' | 'error';
  progress: number;
  error?: string;
  outputFormat?: string;
  convertedSize?: number;
}

export interface ConversionHistoryItem {
  id: string;
  fileName: string;
  originalFormat: string;
  outputFormat: string;
  originalSize: number;
  convertedSize: number;
  timestamp: number;
}

export interface ConversionOptions {
  quality?: number;
}

// Theme type
type Theme = 'dark' | 'light';

const App: React.FC = () => {
  // Theme state - default to dark
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('fileforge-theme');
    return (saved as Theme) || 'dark';
  });

  // File management state
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedFormat, setSelectedFormat] = useState<string>('');
  const [conversionOptions, setConversionOptions] = useState<ConversionOptions>({
    quality: 85,
  });
  const [isConverting, setIsConverting] = useState(false);
  const [conversionHistory, setConversionHistory] = useState<ConversionHistoryItem[]>([]);

  // Custom hook for API operations
  const { uploadFile, convertFile, downloadFile, getFormats, availableFormats } = useFileConvert();

  // Load conversion history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('fileforge-history');
    if (saved) {
      try {
        setConversionHistory(JSON.parse(saved));
      } catch {
        console.error('Failed to parse conversion history');
      }
    }
  }, []);

  // Save conversion history to localStorage
  useEffect(() => {
    localStorage.setItem('fileforge-history', JSON.stringify(conversionHistory));
  }, [conversionHistory]);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.remove('light', 'dark');
    document.documentElement.classList.add(theme);
    localStorage.setItem('fileforge-theme', theme);
  }, [theme]);

  // Fetch available formats on mount
  useEffect(() => {
    getFormats();
  }, [getFormats]);

  // Toggle theme
  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  }, []);

  // Handle file drop
  const handleFilesAdded = useCallback((newFiles: File[]) => {
    const fileItems: FileItem[] = newFiles.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      file,
      name: file.name,
      size: file.size,
      type: file.type || getFileExtension(file.name),
      status: 'pending',
      progress: 0,
    }));
    setFiles((prev) => [...prev, ...fileItems]);
  }, []);

  // Remove a file from the list
  const handleRemoveFile = useCallback((fileId: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  // Get file extension helper
  const getFileExtension = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    return ext;
  };

  // Update file state helper
  const updateFileState = useCallback(
    (fileId: string, updates: Partial<FileItem>) => {
      setFiles((prev) =>
        prev.map((f) => (f.id === fileId ? { ...f, ...updates } : f))
      );
    },
    []
  );

  // Handle conversion process
  const handleConvert = useCallback(async () => {
    if (files.length === 0 || !selectedFormat) return;

    setIsConverting(true);

    for (const fileItem of files) {
      if (fileItem.status === 'completed') continue;

      try {
        // Upload phase
        updateFileState(fileItem.id, { status: 'uploading', progress: 0 });

        const uploadResult = await uploadFile(fileItem.file, (progress) => {
          updateFileState(fileItem.id, { progress: progress * 0.5 }); // 0-50% for upload
        });

        if (!uploadResult.success || !uploadResult.fileId) {
          throw new Error(uploadResult.error || 'Upload failed');
        }

        updateFileState(fileItem.id, {
          status: 'uploaded',
          uploadedId: uploadResult.fileId,
          progress: 50,
        });

        // Conversion phase
        updateFileState(fileItem.id, { status: 'converting' });

        const convertResult = await convertFile(
          uploadResult.fileId,
          selectedFormat,
          conversionOptions,
          (progress) => {
            updateFileState(fileItem.id, { progress: 50 + progress * 0.5 }); // 50-100% for conversion
          }
        );

        if (!convertResult.success || !convertResult.convertedId) {
          throw new Error(convertResult.error || 'Conversion failed');
        }

        updateFileState(fileItem.id, {
          status: 'completed',
          convertedId: convertResult.convertedId,
          outputFormat: selectedFormat,
          convertedSize: convertResult.convertedSize,
          progress: 100,
        });

        // Add to history
        const historyItem: ConversionHistoryItem = {
          id: `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
          fileName: fileItem.name,
          originalFormat: getFileExtension(fileItem.name),
          outputFormat: selectedFormat,
          originalSize: fileItem.size,
          convertedSize: convertResult.convertedSize || 0,
          timestamp: Date.now(),
        };

        setConversionHistory((prev) => [historyItem, ...prev].slice(0, 50));
      } catch (error) {
        updateFileState(fileItem.id, {
          status: 'error',
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    }

    setIsConverting(false);
  }, [files, selectedFormat, conversionOptions, uploadFile, convertFile, updateFileState]);

  // Handle download
  const handleDownload = useCallback(
    async (fileId: string, convertedId: string) => {
      await downloadFile(convertedId);
    },
    [downloadFile]
  );

  // Reset for new conversion
  const handleConvertAnother = useCallback(() => {
    setFiles([]);
    setSelectedFormat('');
  }, []);

  // Clear history
  const handleClearHistory = useCallback(() => {
    setConversionHistory([]);
  }, []);

  // Determine current input file type for format suggestions
  const currentInputType = files.length > 0 ? getFileExtension(files[0].name) : '';

  // Check if all files are completed
  const allCompleted = files.length > 0 && files.every((f) => f.status === 'completed');
  const hasErrors = files.some((f) => f.status === 'error');
  const hasFiles = files.length > 0;
  const canConvert = hasFiles && selectedFormat && !isConverting && !allCompleted;

  // Calculate overall progress
  const overallProgress =
    files.length > 0
      ? files.reduce((sum, f) => sum + f.progress, 0) / files.length
      : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 light:from-gray-50 light:via-white light:to-gray-100 transition-colors duration-300">
      {/* Header */}
      <Header theme={theme} onToggleTheme={toggleTheme} />

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8 max-w-4xl">
        <AnimatePresence mode="wait">
          {!allCompleted ? (
            <motion.div
              key="converter"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              {/* Drop Zone */}
              <DropZone onFilesAdded={handleFilesAdded} disabled={isConverting} />

              {/* File List */}
              {hasFiles && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-6 space-y-3"
                >
                  {files.map((file) => (
                    <FileCard
                      key={file.id}
                      file={file}
                      onRemove={() => handleRemoveFile(file.id)}
                      disabled={isConverting}
                    />
                  ))}
                </motion.div>
              )}

              {/* Format Selector */}
              {hasFiles && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="mt-6"
                >
                  <FormatSelector
                    inputType={currentInputType}
                    selectedFormat={selectedFormat}
                    onFormatChange={setSelectedFormat}
                    quality={conversionOptions.quality || 85}
                    onQualityChange={(quality) =>
                      setConversionOptions((prev) => ({ ...prev, quality }))
                    }
                    availableFormats={availableFormats}
                    disabled={isConverting}
                  />
                </motion.div>
              )}

              {/* Progress Bar */}
              {isConverting && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-6"
                >
                  <ProgressBar progress={overallProgress} />
                </motion.div>
              )}

              {/* Error Display */}
              {hasErrors && !isConverting && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl"
                >
                  <p className="text-red-400 text-sm">
                    Some files failed to convert. Please try again.
                  </p>
                </motion.div>
              )}

              {/* Convert Button */}
              {hasFiles && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="mt-6"
                >
                  <ConvertButton
                    onClick={handleConvert}
                    disabled={!canConvert}
                    isLoading={isConverting}
                    fileCount={files.length}
                  />
                </motion.div>
              )}
            </motion.div>
          ) : (
            /* Download Cards */
            <motion.div
              key="download"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="space-y-4"
            >
              {files.map((file) => (
                <DownloadCard
                  key={file.id}
                  file={file}
                  onDownload={() =>
                    file.convertedId && handleDownload(file.id, file.convertedId)
                  }
                  onConvertAnother={handleConvertAnother}
                />
              ))}
              {files.length > 0 && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
                  onClick={handleConvertAnother}
                  className="w-full py-3 text-slate-400 hover:text-white transition-colors"
                >
                  Convert more files
                </motion.button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Conversion History */}
        {conversionHistory.length > 0 && !isConverting && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-12"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-slate-300">
                Recent Conversions
              </h2>
              <button
                onClick={handleClearHistory}
                className="text-sm text-slate-500 hover:text-slate-300 transition-colors"
              >
                Clear history
              </button>
            </div>
            <div className="space-y-2">
              {conversionHistory.slice(0, 5).map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700/50"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-slate-300 truncate max-w-[200px]">
                      {item.fileName}
                    </span>
                    <span className="text-xs text-slate-500">
                      {item.originalFormat.toUpperCase()} &rarr;{' '}
                      {item.outputFormat.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500">
                    {new Date(item.timestamp).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </main>

      {/* Footer */}
      <footer className="py-8 text-center text-slate-500 text-sm">
        <p>FileForge - Fast, secure file conversion</p>
      </footer>
    </div>
  );
};

export default App;
