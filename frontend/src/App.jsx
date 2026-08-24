import React, { useState, useEffect, useRef } from 'react';
import CodeEditor from './components/CodeEditor';
import RepoInput from './components/RepoInput';
import JobProgress from './components/JobProgress';
import ReportView from './components/ReportView';
import RepoReportView from './components/RepoReportView';
import LoginScreen from './components/LoginScreen';
import HistoryView from './components/HistoryView';
import { submitCodeAnalysis, submitRepoAnalysis, getJobStatus, API_BASE_URL, setToken, clearToken, fetchMe, tryRefresh, logoutServer } from './api/client';
import { connectJobWebSocket } from './api/websocket';

export default function App() {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiOnline, setApiOnline] = useState(null);
  const [me, setMe] = useState(null);
  const [showWelcome, setShowWelcome] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [authError, setAuthError] = useState(null);

  const socketRef = useRef(null);
  const pollRef = useRef(null);

  // Boot: capture OAuth token -> silent refresh (cookie) -> resolve profile
  useEffect(() => {
    fetch(`${API_BASE_URL.replace('/api/v1', '')}/`)
      .then((r) => (r.ok ? setApiOnline(true) : setApiOnline(false)))
      .catch(() => setApiOnline(false));

    const boot = async () => {
      // OAuth callback lands here as /#token=<jwt>
      const hash = new URLSearchParams(window.location.hash.slice(1));
      const incoming = hash.get('token');
      if (incoming) {
        setToken(incoming);
        window.history.replaceState(null, '', window.location.pathname + window.location.search);
      }
      // No stored token? Probe the refresh cookie only for returning users —
      // first-time visitors skip it (avoids a guaranteed 401 in console)
      if (!localStorage.getItem('cp_token') && localStorage.getItem('cp_session')) await tryRefresh();
      setMe(await fetchMe());

      // Returning from a failed/cancelled OAuth attempt -> show the Welcome page
      const err = new URLSearchParams(window.location.search).get('auth_error');
      if (err) {
        setAuthError(err);
        setShowWelcome(true);
      }
    };
    boot();
  }, []);

  const handleLogout = async () => {
    await logoutServer();
    clearToken();
    setMe(null);
  };

  const closeSocket = () => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
  };

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  // Poll job state until a terminal status — used as fallback when WS dies,
  // so the UI never freezes mid-run.
  const startPolling = (jobId) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const jobResult = await getJobStatus(jobId);
        if (jobResult.status) setStatus(jobResult.status);
        if (typeof jobResult.progress === 'number') setProgress(jobResult.progress);

        if (jobResult.status === 'COMPLETED' || jobResult.status === 'CACHE_HIT') {
          setReport(jobResult.data);
          setLoading(false);
          stopPolling();
          closeSocket();
        } else if (jobResult.status === 'FAILED') {
          setError(jobResult.data?.error || 'Job analysis failed.');
          setLoading(false);
          stopPolling();
          closeSocket();
        }
      } catch {
        /* transient — keep polling until terminal or unmount */
      }
    }, 3000);
  };

  useEffect(() => () => { closeSocket(); stopPolling(); }, []);

  // Shared flow: submit a job, then track it over WebSocket (HTTP fallback)
  const runJob = async (submitPromise) => {
    closeSocket();
    stopPolling();
    setLoading(true);
    setError(null);
    setReport(null);
    setStatus('PENDING');
    setProgress(5);

    try {
      const response = await submitPromise;
      const activeJobId = response.job_id;

      socketRef.current = connectJobWebSocket(
        activeJobId,
        (data) => {
          if (data.status) setStatus(data.status);
          if (data.progress !== undefined) setProgress(data.progress);

          if (data.status === 'COMPLETED' || data.status === 'CACHE_HIT') {
            setReport(data.data || data.result);
            setLoading(false);
            closeSocket();
          } else if (data.status === 'FAILED') {
            setError(data.data?.error || data.error || 'Job analysis failed.');
            setLoading(false);
            closeSocket();
          }
        },
        async () => {
          // WebSocket unavailable — keep the UI alive via HTTP polling
          console.warn('WebSocket error, falling back to HTTP polling...');
          startPolling(activeJobId);
        }
      );
    } catch (err) {
      setError(err.message || 'An error occurred while submitting the job.');
      setStatus('FAILED');
      setLoading(false);
    }
  };

  const handleCodeSubmit = ({ title, code, language }) =>
    runJob(submitCodeAnalysis(title, code, language));

  const handleRepoSubmit = ({ githubUrl, file }) =>
    runJob(submitRepoAnalysis(githubUrl, file));

  // The app is usable signed-out; only persistence requires an account
  if (showWelcome) {
    return <LoginScreen authError={authError} onClose={() => setShowWelcome(false)} />;
  }

  if (showHistory) {
    return <HistoryView onClose={() => setShowHistory(false)} />;
  }

  return (
    <>
      {/* Top bar */}
      <header className="border-b border-brand-line bg-brand-surface/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <PulseMark />
            <div className="leading-none">
              <span className="text-[15px] font-semibold text-zinc-900 tracking-tight">
                CodePulse<span className="text-brand-accent">-AI</span>
              </span>
              <span className="hidden sm:block text-[11px] text-zinc-500 mt-1">
                Static analysis · AI audit
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-[11px] font-mono text-zinc-500">
            <span className="hidden md:inline">v0.1.0</span>
            <span className="flex items-center gap-1.5 border border-brand-line rounded-full px-2.5 py-1 bg-brand-bg">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  apiOnline === null
                    ? 'bg-zinc-600 animate-pulse'
                    : apiOnline
                    ? 'bg-brand-accent'
                    : 'bg-red-500'
                }`}
              />
              {apiOnline === null ? 'checking' : apiOnline ? 'api online' : 'api offline'}
            </span>

            {me ? (
              <span className="flex items-center gap-2">
                {me.avatar_url && (
                  <img src={me.avatar_url} alt="" className="w-6 h-6 rounded-full border border-brand-line" />
                )}
                <span className="text-xs text-zinc-600 hidden sm:inline">{me.name || me.email}</span>
                <button
                  onClick={() => setShowHistory(true)}
                  className="border border-brand-line hover:border-zinc-400 text-zinc-700 rounded-md px-2.5 py-1 transition-colors cursor-pointer"
                >
                  History
                </button>
                <button
                  onClick={handleLogout}
                  className="border border-brand-line hover:border-red-300 hover:text-red-500 rounded-md px-2 py-1 transition-colors cursor-pointer"
                >
                  sign out
                </button>
              </span>
            ) : (
              <button
                onClick={() => setShowWelcome(true)}
                className="border border-brand-line hover:border-zinc-400 text-zinc-700 rounded-md px-2.5 py-1 transition-colors cursor-pointer"
              >
                Sign in
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Workspace */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <section className="xl:col-span-5 space-y-4 xl:sticky xl:top-20">
            <CodeEditor onSubmit={handleCodeSubmit} isLoading={loading} />
            <RepoInput onSubmit={handleRepoSubmit} isLoading={loading} />
          </section>

          <section className="xl:col-span-7 space-y-5 min-w-0">
            {status && <JobProgress status={status} progress={progress} error={error} />}
            {report && (
              'summary' in report
                ? <RepoReportView report={report} />
                : <ReportView report={report} />
            )}

            {!status && !report && (
              <EmptyState signedIn={!!me} />
            )}
          </section>
        </div>
      </main>

      {/* Status bar */}
      <footer className="border-t border-brand-line">
        <div className="max-w-7xl mx-auto px-6 h-9 flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>© {new Date().getFullYear()} CodePulse-AI</span>
          <span>{API_BASE_URL}</span>
        </div>
      </footer>
    </>
  );
}

function PulseMark() {
  return (
    <div className="w-8 h-8 rounded-md border border-brand-line bg-brand-raised flex items-center justify-center">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M2 12h4l3-8 4 16 3-8h6"
          stroke="#34d399"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </div>
  );
}

function EmptyState({ signedIn }) {
  return (
    <div className="border border-dashed border-brand-line rounded-lg px-8 py-16 text-center">
      <p className="text-sm text-zinc-500">No report yet.</p>
      <p className="text-xs text-zinc-400 mt-1.5 max-w-xs mx-auto leading-relaxed">
        Paste a snippet on the left and run an analysis. Results stream in live over WebSocket.
      </p>
      {!signedIn && (
        <p className="text-[11px] font-mono text-brand-accent mt-3">Sign in to keep your history</p>
      )}
      {signedIn && (
        <p className="text-[10px] font-mono text-zinc-400 mt-3">scans are saved to your history</p>
      )}
    </div>
  );
}
