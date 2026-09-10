import { useState, useCallback, useRef, useEffect, type FormEvent } from 'react';
import { Youtube, CheckCircle2, XCircle, Loader2, ArrowRight, X, Clipboard, Users } from 'lucide-react';

function isChannelHandle(input: string): boolean {
  const trimmed = input.trim();
  if (trimmed.startsWith('@')) return true;
  if (/^UC[a-zA-Z0-9_-]{22,}$/.test(trimmed)) return true;
  if (trimmed.includes('/channel/') || trimmed.includes('/@')) return true;
  return false;
}

function cleanHandle(input: string): string {
  let h = input.trim();
  if (h.includes('youtube.com/channel/')) h = h.split('/channel/')[1]?.split('/')[0] || h;
  if (h.includes('youtube.com/@')) h = h.split('/@')[1]?.split('/')[0] || h;
  if (h.startsWith('@')) h = h.slice(1);
  return h;
}

interface ValidationResult {
  valid: boolean;
  video_id: string | null;
  normalized_url: string | null;
  url_type: string | null;
  original_url: string | null;
  error: string | null;
}

interface VideoUrlInputProps {
  onValidUrl?: (videoId: string, normalizedUrl: string) => void;
  onChannelDetected?: (handle: string) => void;
  onSubmit?: (videoId: string, normalizedUrl: string) => void;
  isProcessing?: boolean;
}

export default function VideoUrlInput({
  onValidUrl,
  onChannelDetected,
  onSubmit,
  isProcessing = false,
}: VideoUrlInputProps) {
  const [url, setUrl] = useState('');
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState(false);
  const debounceRef = useRef<number | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateUrl = useCallback(async (input: string): Promise<ValidationResult | null> => {
    const trimmed = input.trim();
    if (!trimmed) {
      setValidation(null);
      return null;
    }

    // Detect channel handles client-side
    if (isChannelHandle(trimmed)) {
      const handle = cleanHandle(trimmed);
      const res: ValidationResult = {
        valid: true,
        video_id: null,
        normalized_url: null,
        url_type: 'channel',
        original_url: trimmed,
        error: null,
      };
      setValidation(res);
      if (onChannelDetected) {
        onChannelDetected(handle);
      }
      return res;
    }

    setLoading(true);
    try {
      const resp = await fetch(`/api/validate-url?url=${encodeURIComponent(trimmed)}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        const res: ValidationResult = {
          valid: false,
          video_id: null,
          normalized_url: null,
          url_type: null,
          original_url: trimmed,
          error: body?.error || `Server returned ${resp.status} ${resp.statusText}. Please try again.`,
        };
        setValidation(res);
        return res;
      }
      const data: ValidationResult = await resp.json();
      if (typeof data.valid !== 'boolean') {
        const res: ValidationResult = {
          valid: false,
          video_id: null,
          normalized_url: null,
          url_type: null,
          original_url: trimmed,
          error: 'Unexpected response from server. Please try again.',
        };
        setValidation(res);
        return res;
      }
      setValidation(data);
      if (data.valid && data.video_id && data.normalized_url) {
        onValidUrl?.(data.video_id, data.normalized_url);
      }
      return data;
    } catch (err) {
      const message = err instanceof TypeError
        ? 'Could not reach the server. Check your connection and try again.'
        : `Validation request failed: ${err instanceof Error ? err.message : 'Unknown error'}.`;
      const res: ValidationResult = {
        valid: false,
        video_id: null,
        normalized_url: null,
        url_type: null,
        original_url: trimmed,
        error: message,
      };
      setValidation(res);
      return res;
    } finally {
      setLoading(false);
    }
  }, [onValidUrl, onChannelDetected]);

  const handleChange = (value: string) => {
    setUrl(value);
    setTouched(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => validateUrl(value), 400);
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      handleChange(text);
    } catch {
      // Clipboard API not available
    }
  };

  const handleClear = () => {
    setUrl('');
    setValidation(null);
    setTouched(false);
    inputRef.current?.focus();
  };

  const triggerSubmit = useCallback(async () => {
    if (isProcessing) return;
    const value = (inputRef.current?.value ?? url).trim();
    if (!value) return;

    if (validation?.valid && validation.video_id) {
      if (onSubmit) {
        onSubmit(validation.video_id, validation.normalized_url || value);
      }
      return;
    }

    const res = await validateUrl(value);
    if (res && res.valid && res.video_id && onSubmit) {
      onSubmit(res.video_id, res.normalized_url || value);
    }
  }, [isProcessing, url, validation, onSubmit, validateUrl]);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    triggerSubmit();
  };

  const handleButtonClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    triggerSubmit();
  };

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const statusIcon = () => {
    if (loading) return <Loader2 size={16} className="text-gray-400 animate-spin" />;
    if (!touched || !url) return null;
    if (validation?.valid) return <CheckCircle2 size={16} className="text-emerald-500" />;
    if (validation && !validation.valid) return <XCircle size={16} className="text-red-500" />;
    return null;
  };

  const borderColor = () => {
    if (!touched || !url) return 'border-gray-200 dark:border-gray-700 focus:border-violet-400 dark:focus:border-violet-500';
    if (loading) return 'border-gray-200 dark:border-gray-700';
    if (validation?.valid) return 'border-emerald-400 dark:border-emerald-500';
    if (validation && !validation.valid) return 'border-red-300 dark:border-red-700';
    return 'border-gray-200 dark:border-gray-700';
  };

  return (
    <form onSubmit={handleSubmit} noValidate>
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          YouTube Video URL
        </label>
        <div className="relative">
          <Youtube size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            value={url}
            onChange={(e) => handleChange(e.target.value)}
            onBlur={() => setTouched(true)}
            placeholder="https://youtube.com/watch?v=..."
            disabled={isProcessing}
            className={`w-full pl-10 pr-20 py-3 rounded-xl border-2 text-sm transition-all-200 outline-none bg-white dark:bg-gray-800 focus:ring-4 focus:ring-violet-100 dark:focus:ring-violet-900/30 ${borderColor()} ${isProcessing ? 'opacity-60 cursor-not-allowed' : ''}`}
            autoFocus
            autoComplete="off"
            spellCheck={false}
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
            {url && (
              <button
                type="button"
                onClick={handleClear}
                disabled={isProcessing}
                className="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all-200 disabled:opacity-50"
                aria-label="Clear input"
              >
                <X size={14} />
              </button>
            )}
            <button
              type="button"
              onClick={handlePaste}
              disabled={isProcessing}
              className="p-1 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all-200 disabled:opacity-50"
              aria-label="Paste from clipboard"
            >
              <Clipboard size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Validation feedback */}
      {touched && url && !loading && validation && (
        <div
          className={`mb-5 px-4 py-3 rounded-xl border text-sm ${
            validation.url_type === 'channel'
              ? 'bg-violet-50 dark:bg-violet-900/20 border-violet-200 dark:border-violet-800 text-violet-700 dark:text-violet-300'
              : validation.valid
              ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-600 dark:text-red-400'
          }`}
        >
          <div className="flex items-start gap-2.5">
            {validation.url_type === 'channel' ? (
              <Users size={16} className="mt-0.5 flex-shrink-0 text-violet-500" />
            ) : validation.valid ? (
              <CheckCircle2 size={16} className="mt-0.5 flex-shrink-0 text-emerald-500" />
            ) : (
              <XCircle size={16} className="mt-0.5 flex-shrink-0 text-red-500" />
            )}
            <div>
              {validation.url_type === 'channel' ? (
                <>
                  <span className="font-medium">Channel detected</span>
                  <div className="mt-0.5 text-xs opacity-75">
                    Fetching transcripts for all videos in this channel...
                  </div>
                </>
              ) : validation.valid ? (
                <>
                  <span className="font-medium">Valid URL</span>
                  <div className="mt-0.5 font-mono text-xs opacity-75">
                    Video ID: {validation.video_id}
                  </div>
                </>
              ) : (
                <span>{validation.error || 'Invalid YouTube video URL.'}</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Status indicator row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          {isProcessing && (
            <span className="text-violet-600 dark:text-violet-400 font-medium inline-flex items-center gap-1.5">
              <Loader2 size={12} className="animate-spin" />
              Processing transcript...
            </span>
          )}
          {!isProcessing && loading && <Loader2 size={12} className="animate-spin" />}
          {!isProcessing && statusIcon()}
          {!isProcessing && validation?.valid && !loading && (
            <span className="text-emerald-600 dark:text-emerald-400 font-medium">
              Ready to process
            </span>
          )}
          {!isProcessing && validation && !validation.valid && !loading && (
            <span className="text-red-500 font-medium">{validation.error || 'Unsupported URL'}</span>
          )}
        </div>

        <button
          type="button"
          onClick={handleButtonClick}
          disabled={!validation?.valid || isProcessing}
          className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all-200 ${
            validation?.valid && !isProcessing
              ? 'bg-violet-600 text-white hover:bg-violet-500 active:bg-violet-700 shadow-lg shadow-violet-200 dark:shadow-violet-900/30 hover:shadow-xl cursor-pointer'
              : 'bg-gray-200 dark:bg-gray-800 text-gray-400 dark:text-gray-600 cursor-not-allowed'
          }`}
        >
          {isProcessing ? (
            <>
              <Loader2 size={15} className="animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Continue
              <ArrowRight size={15} />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
