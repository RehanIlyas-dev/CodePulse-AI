import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../api/client';
import ReportView from './ReportView';
import RepoReportView from './RepoReportView';

export default function HistoryView({ onClose }) {
  const [scans, setScans] = useState([]);
  const [repoScans, setRepoScans] = useState([]);
  const [activeTab, setActiveTab] = useState('scans');
  const [selectedScan, setSelectedScan] = useState(null);
  const [selectedRepoScan, setSelectedRepoScan] = useState(null);
  const [loading, setLoading] = useState(true);

  // Handle browser back button for detail views
  useEffect(() => {
    const handlePopState = () => {
      if (selectedScan) setSelectedScan(null);
      if (selectedRepoScan) setSelectedRepoScan(null);
    };

    // Push state when detail view opens
    if (selectedScan) {
      window.history.pushState({ scanId: selectedScan.id }, '');
    } else if (selectedRepoScan) {
      window.history.pushState({ repoScanId: selectedRepoScan.id }, '');
    }

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [selectedScan, selectedRepoScan]);

  useEffect(() => {
    const loadHistory = async () => {
      setLoading(true);
      try {
        const [scansRes, repoScansRes] = await Promise.all([
          fetch(`${API_BASE_URL}/scans?limit=20`, { headers: { Authorization: `Bearer ${localStorage.getItem('cp_token')}` }}),
          fetch(`${API_BASE_URL}/repo-scans?limit=20`, { headers: { Authorization: `Bearer ${localStorage.getItem('cp_token')}` }})
        ]);
        const [scansData, repoScansData] = await Promise.all([
          scansRes.json(),
          repoScansRes.json()
        ]);
        setScans(scansData);
        setRepoScans(repoScansData);
      } catch (err) {
        console.error('Failed to load history:', err);
      } finally {
        setLoading(false);
      }
    };
    loadHistory();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-brand-bg flex items-center justify-center font-sans">
        <div className="w-8 h-8 border-2 border-brand-line border-t-brand-accent rounded-full animate-spin" />
      </div>
    );
  }

  const closeDetail = () => {
    setSelectedScan(null);
    setSelectedRepoScan(null);
  };

  return (
    <div className="min-h-screen bg-brand-bg flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-brand-line bg-brand-surface/60 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
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
            <div className="leading-none">
              <span className="text-[15px] font-semibold text-zinc-900 tracking-tight">
                CodePulse<span className="text-brand-accent">-AI</span>
              </span>
              <span className="hidden sm:block text-[11px] text-zinc-500 mt-1">
                Analysis History
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="border border-brand-line hover:border-zinc-400 text-zinc-700 rounded-md px-2.5 py-1 transition-colors cursor-pointer"
            >
              ← Back
            </button>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8">
        <div className="space-y-6">
          {/* Tabs */}
          <div className="flex gap-4 border-b border-brand-line mb-6">
            <button
              onClick={() => setActiveTab('scans')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === 'scans'
                  ? 'bg-brand-accent text-zinc-950'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Code Scans ({scans.length})
            </button>
            <button
              onClick={() => setActiveTab('repo-scans')}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
                activeTab === 'repo-scans'
                  ? 'bg-brand-accent text-zinc-950'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Repo Scans ({repoScans.length})
            </button>
          </div>

          {/* Scan Detail View */}
          {selectedScan && (
            <ReportView report={selectedScan} onClose={closeDetail} />
          )}

          {selectedRepoScan && (
            <RepoReportView report={selectedRepoScan} onClose={closeDetail} />
          )}

          {/* History Lists */}
          {!selectedScan && !selectedRepoScan && (
            <div className="space-y-4">
              {activeTab === 'scans' ? (
                <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
                  {scans.length === 0 ? (
                    <div className="px-5 py-8 text-center text-zinc-500">
                      No code scans yet. Run an analysis to see your history here.
                    </div>
                  ) : (
                    <ul className="divide-y divide-brand-line">
                      {scans.map((scan) => (
                        <li
                          key={scan.id}
                          onClick={() => setSelectedScan(scan)}
                          className="px-5 py-4 hover:bg-brand-raised cursor-pointer"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-400">
                                {scan.language}
                              </span>
                              <span className="font-medium text-zinc-100 truncate max-w-[300px]">
                                {scan.title}
                              </span>
                            </div>
                            <div className="flex items-center gap-4 text-xs text-zinc-400 font-mono">
                              <span>{scan.ast_metrics?.total_lines || 0} lines</span>
                              <span>{scan.ast_metrics?.function_count || 0} fn</span>
                              <span>cx {scan.ast_metrics?.cyclomatic_complexity || 1}</span>
                              <span className="text-brand-accent">
                                {scan.security_score || 0}/100
                              </span>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
                  {repoScans.length === 0 ? (
                    <div className="px-5 py-8 text-center text-zinc-500">
                      No repository scans yet. Analyze a repository to see history here.
                    </div>
                  ) : (
                    <ul className="divide-y divide-brand-line">
                      {repoScans.map((scan) => (
                        <li
                          key={scan.id}
                          onClick={() => setSelectedRepoScan(scan)}
                          className="px-5 py-3.5 hover:bg-brand-raised cursor-pointer"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-[11px] font-mono text-zinc-500 flex-shrink-0">
                              {scan.source.startsWith('http') ? 'GitHub' : 'ZIP upload'}
                            </span>
                            <span className="font-medium text-zinc-100 truncate">
                              {scan.source}
                            </span>
                            <div className="ml-auto flex items-center gap-4 text-xs text-zinc-400 font-mono">
                              <span>{scan.summary?.total_files || 0} files</span>
                              <span>{scan.summary?.total_loc?.toLocaleString() || 0} LOC</span>
                              <span className="text-brand-accent">
                                Arch: {scan.architecture_score || 0}/100
                              </span>
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}