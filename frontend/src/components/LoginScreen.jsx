import React from 'react';
import { API_BASE_URL } from '../api/client';

export default function LoginScreen({ authError, onClose }) {
  return (
    <div className="min-h-screen bg-brand-bg flex items-center justify-center px-4 font-sans">
      <div className="w-full max-w-sm relative">
        {onClose && (
          <button
            onClick={onClose}
            className="absolute -top-1 right-0 text-[11px] font-mono text-zinc-400 hover:text-zinc-700 transition-colors cursor-pointer"
          >
            ← back
          </button>
        )}
        {/* Brand */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-12 h-12 rounded-lg border border-brand-line bg-brand-surface flex items-center justify-center mb-5">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden>
              <path
                d="M2 12h4l3-8 4 16 3-8h6"
                stroke="#059669"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <p className="text-[11px] font-mono uppercase tracking-[0.2em] text-zinc-400 mb-2">
            Welcome to
          </p>
          <h1 className="text-2xl font-bold text-zinc-900 tracking-tight">
            CodePulse<span className="text-brand-accent">-AI</span>
          </h1>
          <p className="text-xs text-zinc-500 mt-3 leading-relaxed max-w-[260px]">
            Static analysis and AI code audit. Sign in to run your first scan.
          </p>
        </div>

        {/* Error banner */}
        {authError && (
          <div className="mb-4 border border-red-300 bg-red-50 rounded-md px-3 py-2">
            <p className="text-xs font-mono text-red-600 text-center">
              {authError === 'denied' ? 'Sign-in was cancelled.' :
               authError === 'bad_state' ? 'Session expired — try again.' :
               authError === 'no_email' ? 'No email shared by provider.' :
               authError === 'token_exchange' ? 'Provider handshake failed.' :
               'Sign-in failed. Please retry.'}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2.5">
          <a
            href={`${API_BASE_URL}/auth/login/google`}
            className="flex items-center justify-center gap-2.5 w-full bg-brand-surface border border-brand-line hover:border-zinc-400 text-sm text-zinc-800 py-2.5 rounded-md transition-colors"
          >
            <GoogleMark />
            Continue with Google
          </a>
          <a
            href={`${API_BASE_URL}/auth/login/github`}
            className="flex items-center justify-center gap-2.5 w-full bg-zinc-900 hover:bg-black text-white text-sm py-2.5 rounded-md transition-colors"
          >
            <GitHubMark />
            Continue with GitHub
          </a>
        </div>

        {/* Footer note */}
        <p className="text-[10px] font-mono text-zinc-400 text-center mt-6 leading-relaxed">
          No passwords here — authentication is handled<br />by Google or GitHub.
        </p>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" aria-hidden>
      <path fill="#FFC107" d="M43.6 20H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 13 4 4 13 4 24s9 20 20 20 20-9 20-20c0-1.3-.1-2.7-.4-4z"/>
      <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3l5.7-5.7C34.3 6.1 29.4 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/>
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/>
      <path fill="#1976D2" d="M43.6 20H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.1 5.7l6.2 5.2C41.4 34.9 44 30 44 24c0-1.3-.1-2.7-.4-4z"/>
    </svg>
  );
}

function GitHubMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden>
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
    </svg>
  );
}
