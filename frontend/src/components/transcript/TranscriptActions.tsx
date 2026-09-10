import { useState } from 'react';
import { Copy, Check, Download, FileText, Languages } from 'lucide-react';
import type { TranscriptResult } from '../../types';

interface TranscriptActionsProps {
  transcript: TranscriptResult;
  allTranscripts?: Record<string, TranscriptResult>;
}

function getLanguageLabel(code: string): string {
  const labels: Record<string, string> = { en: 'English', hi: 'Hindi' };
  return labels[code] || code.toUpperCase();
}

export default function TranscriptActions({ transcript, allTranscripts = {} }: TranscriptActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(transcript.plain_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  };

  const handleDownload = (format: 'txt' | 'json') => {
    let content: string;
    let mime: string;
    let ext: string;

    if (format === 'json') {
      content = JSON.stringify(transcript, null, 2);
      mime = 'application/json';
      ext = 'json';
    } else {
      content = transcript.plain_text;
      mime = 'text/plain';
      ext = 'txt';
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${transcript.video_id}_transcript_${transcript.language}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadLanguage = (lang: string, t: TranscriptResult) => {
    const blob = new Blob([t.plain_text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${t.video_id}_transcript_${lang}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const otherTranscripts = Object.entries(allTranscripts).filter(
    ([code]) => code !== transcript.language
  );

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleCopy}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 active:bg-gray-100 dark:active:bg-gray-600 transition-all-200"
      >
        {copied ? (
          <>
            <Check size={13} className="text-emerald-500" />
            Copied
          </>
        ) : (
          <>
            <Copy size={13} />
            Copy
          </>
        )}
      </button>

      <div className="relative group">
        <button className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-medium border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 active:bg-gray-100 dark:active:bg-gray-600 transition-all-200">
          <Download size={13} />
          Download
          <svg width="8" height="8" viewBox="0 0 8 8" fill="none" className="ml-0.5">
            <path d="M2 3L4 5L6 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
        <div className="absolute right-0 top-full mt-1 w-44 py-1.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all-200 z-10">
          {Object.entries(allTranscripts).map(([code, t]) => (
            <button
              key={code}
              onClick={() => handleDownloadLanguage(code, t)}
              className="flex items-center gap-2 w-full px-3.5 py-2 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <Languages size={13} />
              {getLanguageLabel(code)} Transcript (.txt)
            </button>
          ))}
          <div className="border-t border-gray-100 dark:border-gray-700 my-1 mx-3" />
          <button
            onClick={() => handleDownload('txt')}
            className="flex items-center gap-2 w-full px-3.5 py-2 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <FileText size={13} />
            Plain Text (.txt)
          </button>
          <button
            onClick={() => handleDownload('json')}
            className="flex items-center gap-2 w-full px-3.5 py-2 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <FileText size={13} />
            JSON (.json)
          </button>
        </div>
      </div>
    </div>
  );
}