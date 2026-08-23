import React, { useState, useEffect, useRef } from 'react';
import CodeEditor from './components/CodeEditor';
import RepoInput from './components/RepoInput';
import JobProgress from './components/JobProgress';
import ReportView from './components/ReportView';
import RepoReportView from './components/RepoReportView';
import LoginScreen from './components/LoginScreen';
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
  const [booting, setBooting] = useState(true);

  const socketRef = useRef(null);

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
      // No stored token? Try the httpOnly refresh cookie before giving up
      if (!localStorage.getItem('cp_token')) await tryRefresh();
      const user = await fetchMe();
      setMe(user);
      setBooting(false);
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

  useEffect(() => () => closeSocket(), []);

  // Shared flow: submit a job, then track it over WebSocket (HTTP fallback)
  const runJob = async (submitPromise) => {
    closeSocket();
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
          // WebSocket unavailable — fall back to one HTTP poll
          console.warn('WebSocket error, falling back to HTTP polling...');
          try {
            const jobResult = await getJobStatus(activeJobId);
            setStatus(jobResult.status);
            if (jobResult.data) setReport(jobResult.data);
          } catch {
            setError('Failed to track job progress via fallback.');
          } finally {
            setLoading(false);
            closeSocket();
          }
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

  // Auth gate: splash while booting, login screen when signed out
  if (booting) {
    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center font-sans">
        <div className="w-8 h-8 border-2 border-brand-line border-t-brand-accent rounded-full animate-spin" />
      </div>
    );
  }

  if (!me) {
    const params = new URLSearchParams(window.location.search);
    return <LoginScreen authError={params.get('auth_error')} />;
  }

  return (
    <div className="min-h-screen bg-brand-bg flex flex-col font-sans">
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

            {me && (
              <span className="flex items-center gap-2">
                {me.avatar_url && (
                  <img src={me.avatar_url} alt="" className="w-6 h-6 rounded-full border border-brand-line" />
                )}
                <span className="text-xs text-zinc-600 hidden sm:inline">{me.name || me.email}</span>
                <button
                  onClick={handleLogout}
                  className="border border-brand-line hover:border-red-300 hover:text-red-500 rounded-md px-2 py-1 transition-colors cursor-pointer"
                >
                  sign out
                </button>
              </span>
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
              <EmptyState />
            )}
          </section>
        </div>
      </main>

      {/* Status bar */}
      <footer className="border-t border-brand-line">
        <div className="max-w-7xl mx-auto px-6 h-9 flex items-center justify-between text-[11px] font-mono text-zinc-400">
          <span>© {new Date().getFullYear()} CodePulse-AI</span>
          <span>localhost:8000/api/v1</span>
        </div>
      </footer>
    </div>
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

function EmptyState() {
  return (
    <div className="border border-dashed border-brand-line rounded-lg px-8 py-16 text-center">
      <p className="text-sm text-zinc-500">No report yet.</p>
      <p className="text-xs text-zinc-400 mt-1.5 max-w-xs mx-auto leading-relaxed">
        Paste a snippet on the left and run an analysis. Results stream in live over WebSocket.
      </p>
    </div>
  );
}
