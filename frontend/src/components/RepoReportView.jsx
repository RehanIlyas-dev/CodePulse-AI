import React, { useMemo, useState } from 'react';
import { Check, Copy, FolderGit2, ChevronDown } from 'lucide-react';

const LANG_BADGE = {
  python: 'border-sky-500/40 bg-sky-500/10 text-sky-600',
  javascript: 'border-amber-500/40 bg-amber-500/10 text-amber-600',
  typescript: 'border-blue-500/40 bg-blue-500/10 text-blue-600',
  rust: 'border-orange-500/40 bg-orange-500/10 text-orange-600',
  go: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-600',
  ruby: 'border-red-500/40 bg-red-500/10 text-red-600',
};

const ISSUE_BADGE = {
  security: 'border-red-500/40 bg-red-500/10 text-red-600',
  bug: 'border-orange-500/40 bg-orange-500/10 text-orange-600',
  performance: 'border-amber-500/40 bg-amber-500/10 text-amber-600',
  style: 'border-sky-500/40 bg-sky-500/10 text-sky-600',
};

function scoreTone(v) {
  if (v == null) return 'bg-zinc-400';
  if (v >= 80) return 'bg-brand-accent-strong';
  if (v >= 50) return 'bg-amber-400';
  return 'bg-red-500';
}

export default function RepoReportView({ report }) {
  const [copied, setCopied] = useState(false);
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [openFile, setOpenFile] = useState(null);

  const summary = report.summary || {};
  const files = useMemo(
    () => Object.entries(report.files || {}).map(([path, info]) => ({ path, ...info })),
    [report.files]
  );
  const visibleFiles = showAllFiles ? files : files.slice(0, 8);
  const suggestions = report.refactored_suggestions || '';

  const copySuggestions = () => {
    navigator.clipboard.writeText(suggestions);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-5">
      {/* Header + scores */}
      <div className="bg-brand-surface border border-brand-line rounded-lg p-5">
        <div className="flex items-center gap-2.5 mb-4 min-w-0">
          <FolderGit2 size={15} className="text-brand-accent shrink-0" />
          <span className="text-[13px] font-semibold text-zinc-800 truncate" title={report.source}>
            {report.source}
          </span>
        </div>

        <div className="grid sm:grid-cols-2 gap-x-8 gap-y-4">
          <ScoreBar label="Architecture" value={report.architecture_score} />
          <ScoreBar label="Maintainability" value={report.maintainability_score} />
        </div>

        <div className="mt-5 pt-4 border-t border-brand-line grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Files" value={summary.total_files} />
          <Stat label="Lines" value={summary.total_loc?.toLocaleString()} />
          <Stat label="Functions" value={summary.total_functions} />
          <Stat label="Avg complexity" value={summary.average_complexity} mono small />
        </div>
      </div>

      {/* Per-file breakdown */}
      {files.length > 0 && (
        <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
          <div className="px-5 h-11 flex items-center justify-between border-b border-brand-line">
            <h2 className="text-[13px] font-semibold text-zinc-800">
              Files
              <span className="ml-2 text-[11px] font-mono text-zinc-400">{files.length}</span>
            </h2>
            <span className="text-[10px] font-mono text-zinc-400">click a file for its audit</span>
          </div>
          <ul className="divide-y divide-brand-line">
            {visibleFiles.map((f) => {
              const m = f.metrics || {};
              const ai = f.ai || null;
              const lang = (f.language || '?').toLowerCase();
              const isOpen = openFile === f.path;
              return (
                <li key={f.path}>
                  <button
                    onClick={() => setOpenFile(isOpen ? null : f.path)}
                    className={`w-full px-5 py-2.5 flex items-center gap-3 min-w-0 text-left hover:bg-brand-raised transition-colors cursor-pointer ${
                      isOpen ? 'bg-brand-raised' : ''
                    }`}
                  >
                    <span
                      className={`text-[9px] font-mono uppercase border rounded px-1 py-0.5 shrink-0 ${
                        LANG_BADGE[lang] || 'border-brand-line bg-brand-raised text-zinc-500'
                      }`}
                    >
                      {lang}
                    </span>
                    <span
                      className="flex-1 text-xs font-mono text-zinc-700 truncate"
                      title={f.path}
                    >
                      {f.path}
                    </span>
                    {ai && (
                      <span
                        className={`text-[9px] font-mono uppercase border rounded px-1 py-0.5 shrink-0 ${
                          ISSUE_BADGE[(ai.issues?.[0]?.type)] || 'border-brand-line bg-brand-raised text-zinc-500'
                        }`}
                        title={`${ai.issues?.length ?? 0} findings`}
                      >
                        {ai.issues?.length ?? 0} find
                      </span>
                    )}
                    <span className="text-[11px] font-mono text-zinc-400 tabular-nums shrink-0 hidden sm:inline">
                      {m.total_lines ?? '—'} ln · cx {m.cyclomatic_complexity ?? '—'}
                    </span>
                    <ChevronDown
                      size={13}
                      className={`shrink-0 text-zinc-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                    />
                  </button>

                  {/* Expanded per-file AI audit */}
                  {isOpen && (
                    <div className="px-5 pb-4 pt-1 border-t border-brand-line/60 bg-brand-bg/50">
                      {!ai ? (
                        <p className="text-xs text-zinc-400 py-2">
                          Deep analysis unavailable for this file (metrics only).
                        </p>
                      ) : (
                        <FileAudit ai={ai} />
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {files.length > 8 && (
            <button
              onClick={() => setShowAllFiles((v) => !v)}
              className="w-full px-5 h-9 text-[11px] font-mono text-zinc-400 hover:text-zinc-700 hover:bg-brand-raised transition-colors cursor-pointer border-t border-brand-line"
            >
              {showAllFiles ? 'show less −' : `show all ${files.length} files +`}
            </button>
          )}
        </div>
      )}

      {/* Refactor suggestions */}
      {suggestions && (
        <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
          <div className="px-5 h-11 flex items-center justify-between border-b border-brand-line">
            <h2 className="text-[13px] font-semibold text-zinc-800">Improvement plan</h2>
            <button
              onClick={copySuggestions}
              className="flex items-center gap-1.5 text-xs font-mono text-zinc-400 hover:text-zinc-700 border border-brand-line hover:border-zinc-300 rounded-md px-2.5 py-1 transition-colors cursor-pointer"
            >
              {copied ? (
                <><Check size={12} className="text-brand-accent" /> copied</>
              ) : (
                <><Copy size={12} /> copy</>
              )}
            </button>
          </div>
          <pre className="p-5 overflow-x-auto text-xs leading-relaxed font-mono text-emerald-800 whitespace-pre-wrap">
            <code>{suggestions}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

function ScoreBar({ label, value }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1.5">
        <span className="text-xs text-zinc-500">{label}</span>
        <span className="text-sm font-semibold text-zinc-900 tabular-nums">
          {value ?? '—'}<span className="text-[10px] text-zinc-400 font-normal">/100</span>
        </span>
      </div>
      <div className="h-1 rounded-full bg-brand-line overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${scoreTone(value)}`}
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
    </div>
  );
}

function Stat({ label, value, mono, small }) {
  return (
    <div>
      <p className="text-[10px] font-mono uppercase tracking-wider text-zinc-400">{label}</p>
      <p
        className={`mt-0.5 font-semibold text-zinc-900 ${
          small ? 'text-xs font-mono' : 'text-base tabular-nums'
        }`}
      >
        {value ?? '—'}
      </p>
    </div>
  );
}

function FileAudit({ ai }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(ai.refactored_code || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="py-3 space-y-4">
      {/* Complexity + scores */}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <span className="text-[11px] font-mono text-zinc-500">
          time <b className="text-zinc-800">{ai.time_complexity}</b> · space{' '}
          <b className="text-zinc-800">{ai.space_complexity}</b>
        </span>
        <MiniBar label="Security" value={ai.security_score} />
        <MiniBar label="Maintainability" value={ai.maintainability_score} />
      </div>

      {/* Issues */}
      {ai.issues?.length > 0 && (
        <ul className="space-y-2">
          {ai.issues.map((issue, idx) => {
            const type = (issue.type || 'info').toLowerCase();
            return (
              <li key={idx} className="bg-brand-surface border border-brand-line rounded-md p-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[9px] font-mono uppercase border rounded px-1 py-0.5 ${
                      ISSUE_BADGE[type] || 'border-brand-line bg-brand-raised text-zinc-500'
                    }`}
                  >
                    {type}
                  </span>
                  {issue.line_number != null && (
                    <span className="text-[10px] font-mono text-zinc-400">line {issue.line_number}</span>
                  )}
                </div>
                <p className="text-xs text-zinc-700 leading-relaxed">{issue.description}</p>
                {issue.suggestion && (
                  <p className="mt-0.5 text-[11px] text-zinc-500 leading-relaxed">
                    <span className="text-brand-accent">→</span> {issue.suggestion}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {/* Refactored code */}
      {ai.refactored_code && (
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-400">
              Refactored
            </span>
            <button
              onClick={copy}
              className="flex items-center gap-1 text-[10px] font-mono text-zinc-400 hover:text-zinc-700 cursor-pointer"
            >
              {copied ? (
                <><Check size={10} className="text-brand-accent" /> copied</>
              ) : (
                <><Copy size={10} /> copy</>
              )}
            </button>
          </div>
          <pre className="bg-brand-surface border border-brand-line rounded-md p-3 overflow-x-auto text-[11px] leading-relaxed font-mono text-emerald-800 max-h-60 overflow-y-auto">
            <code>{ai.refactored_code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

function MiniBar({ label, value }) {
  const tone =
    value == null ? 'bg-zinc-300'
    : value >= 80 ? 'bg-brand-accent-strong'
    : value >= 50 ? 'bg-amber-400'
    : 'bg-red-500';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400">{label}</span>
      <div className="w-20 h-1 rounded-full bg-brand-line overflow-hidden">
        <div className={`h-full ${tone}`} style={{ width: `${value ?? 0}%` }} />
      </div>
      <span className="text-[11px] font-mono tabular-nums text-zinc-600">{value ?? '—'}</span>
    </div>
  );
}
