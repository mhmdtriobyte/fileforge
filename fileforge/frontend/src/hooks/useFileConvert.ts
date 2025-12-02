/**
 * useFileConvert.ts - File Conversion API Hook
 *
 * Custom hook providing file upload, conversion, and download
 * functionality with progress tracking and error handling.
 */

import { useState, useCallback } from 'react';
import axios, { AxiosProgressEvent } from 'axios';

// API base URL - configurable via environment variable
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Types
export interface UploadResult {
  success: boolean;
  fileId?: string;
  error?: string;
}

export interface ConvertResult {
  success: boolean;
  convertedId?: string;
  convertedSize?: number;
  error?: string;
}

export interface ConversionOptions {
  quality?: number;
  [key: string]: unknown;
}

export interface ConversionStatus {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
}

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minute timeout for large files
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Custom hook for file conversion operations
 */
export function useFileConvert() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availableFormats, setAvailableFormats] = useState<Record<string, string[]>>({});

  /**
   * Upload a file to the server
   */
  const uploadFile = useCallback(
    async (
      file: File,
      onProgress?: (progress: number) => void
    ): Promise<UploadResult> => {
      setIsLoading(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await api.post('/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          onUploadProgress: (progressEvent: AxiosProgressEvent) => {
            if (progressEvent.total && onProgress) {
              const progress = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              onProgress(progress / 100);
            }
          },
        });

        setIsLoading(false);

        // Backend returns file_id directly (not wrapped in success)
        if (response.data.file_id) {
          return {
            success: true,
            fileId: response.data.file_id,
          };
        }

        return {
          success: false,
          error: response.data.detail || 'Upload failed',
        };
      } catch (err) {
        setIsLoading(false);
        const errorMessage =
          axios.isAxiosError(err) && err.response?.data?.detail
            ? err.response.data.detail
            : err instanceof Error
            ? err.message
            : 'Upload failed';

        setError(errorMessage);
        return {
          success: false,
          error: errorMessage,
        };
      }
    },
    []
  );

  /**
   * Convert a file to a different format
   */
  const convertFile = useCallback(
    async (
      fileId: string,
      outputFormat: string,
      options: ConversionOptions = {},
      onProgress?: (progress: number) => void
    ): Promise<ConvertResult> => {
      setIsLoading(true);
      setError(null);

      try {
        // Start conversion - backend expects file_id and output_format
        const response = await api.post('/convert', {
          file_id: fileId,
          output_format: outputFormat,
          options,
        });

        // Backend returns output_file_id and status directly
        if (response.data.status === 'completed' && response.data.output_file_id) {
          // Conversion is synchronous in this backend, so it completes immediately
          if (onProgress) {
            onProgress(1); // 100%
          }

          setIsLoading(false);
          return {
            success: true,
            convertedId: response.data.output_file_id,
          };
        }

        // If not completed, poll for status
        const result = await pollConversionStatus(fileId, onProgress);

        setIsLoading(false);

        if (result.status === 'completed') {
          return {
            success: true,
            convertedId: result.convertedId,
            convertedSize: result.convertedSize,
          };
        }

        return {
          success: false,
          error: result.error || 'Conversion failed',
        };
      } catch (err) {
        setIsLoading(false);
        const errorMessage =
          axios.isAxiosError(err) && err.response?.data?.detail
            ? err.response.data.detail
            : err instanceof Error
            ? err.message
            : 'Conversion failed';

        setError(errorMessage);
        return {
          success: false,
          error: errorMessage,
        };
      }
    },
    []
  );

  /**
   * Poll conversion status until completion
   */
  const pollConversionStatus = async (
    fileId: string,
    onProgress?: (progress: number) => void
  ): Promise<{
    status: string;
    convertedId?: string;
    convertedSize?: number;
    error?: string;
  }> => {
    const maxAttempts = 120; // 2 minutes with 1 second intervals
    let attempts = 0;

    while (attempts < maxAttempts) {
      try {
        // Backend uses /progress/{file_id} endpoint
        const response = await api.get(`/progress/${fileId}`);
        const { status, progress, output_file_id, error: statusError } = response.data;

        if (onProgress && typeof progress === 'number') {
          onProgress(progress / 100);
        }

        if (status === 'completed') {
          return { status, convertedId: output_file_id };
        }

        if (status === 'failed') {
          return { status, error: statusError || 'Conversion failed' };
        }

        // Wait before next poll
        await new Promise((resolve) => setTimeout(resolve, 1000));
        attempts++;
      } catch (err) {
        // On error, wait and retry
        await new Promise((resolve) => setTimeout(resolve, 2000));
        attempts++;

        if (attempts >= maxAttempts) {
          return { status: 'failed', error: 'Conversion timed out' };
        }
      }
    }

    return { status: 'failed', error: 'Conversion timed out' };
  };

  /**
   * Download a converted file
   */
  const downloadFile = useCallback(async (fileId: string): Promise<void> => {
    try {
      const response = await api.get(`/download/${fileId}`, {
        responseType: 'blob',
      });

      // Extract filename from Content-Disposition header or use default
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'converted-file';

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create download link
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Download failed';
      setError(errorMessage);
      throw new Error(errorMessage);
    }
  }, []);

  /**
   * Get available conversion formats
   */
  const getFormats = useCallback(async (): Promise<Record<string, string[]>> => {
    try {
      const response = await api.get('/formats');

      // Backend returns { conversions: { format: { outputs: [...], category: '...' } } }
      if (response.data.conversions) {
        const formats: Record<string, string[]> = {};
        for (const [format, info] of Object.entries(response.data.conversions)) {
          formats[format] = (info as { outputs: string[] }).outputs;
        }
        setAvailableFormats(formats);
        return formats;
      }

      return {};
    } catch (err) {
      console.error('Failed to fetch formats:', err);
      // Return empty object on error, component will use defaults
      return {};
    }
  }, []);

  /**
   * Get conversion status
   */
  const getStatus = useCallback(
    async (conversionId: string): Promise<ConversionStatus> => {
      try {
        const response = await api.get(`/convert/status/${conversionId}`);
        return response.data;
      } catch (err) {
        return {
          status: 'failed',
          progress: 0,
          error: err instanceof Error ? err.message : 'Failed to get status',
        };
      }
    },
    []
  );

  /**
   * Cancel an ongoing conversion
   */
  const cancelConversion = useCallback(
    async (conversionId: string): Promise<boolean> => {
      try {
        const response = await api.post(`/convert/cancel/${conversionId}`);
        return response.data.success || false;
      } catch (err) {
        console.error('Failed to cancel conversion:', err);
        return false;
      }
    },
    []
  );

  return {
    // State
    isLoading,
    error,
    availableFormats,

    // Methods
    uploadFile,
    convertFile,
    downloadFile,
    getFormats,
    getStatus,
    cancelConversion,

    // Utilities
    clearError: () => setError(null),
  };
}

export default useFileConvert;
