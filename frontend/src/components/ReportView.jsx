import React, { useMemo, useState } from 'react';
import { Check, Copy } from 'lucide-react';

const TYPE_STYLES = {
  security: 'border-red-500/40 bg-red-500/10 text-red-400',
  bug: 'border-orange-500/40 bg-orange-500/10 text-orange-400',
  performance: 'border-amber-500/40 bg-amber-500/10 text-amber-400',
  style: 'border-sky-500/40 bg-sky-500/10 text-sky-400',
};

function scoreTone(v) {
  if (v == null) return 'bg-zinc-600';
  if (v >= 80) return 'bg-brand-accent-strong';
  if (v >= 50) return 'bg-amber-400';
  return 'bg-red-500';
}

// Turn the plain-text report into {heading, body} sections.
function parseReportDoc(text) {
  const sections = [];
  let current = { heading: null, body: [] };
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (/^[=\-]{4,}$/.test(line)) continue; // decorative separators
    const isHeading =
      line.length >= 3 && line === line.toUpperCase() && /[A-Z]/.test(line);
    if (isHeading) {
      if (current.heading || current.body.length) sections.push(current);
      current = { heading: line.replace(/^-+\s*|\s*-+$/g, '').trim(), body: [] };
    } else if (line) {
      current.body.push(raw.trimEnd());
    }
  }
  if (current.heading || current.body.length) sections.push(current);
  return sections;
}

export default function ReportView({ report }) {
  const [copied, setCopied] = useState(false);
  const [showDoc, setShowDoc] = useState(false);

  const ast = report.ast_metrics || {};
  const issues = report.issues_list || [];
  const refactoredCode = report.refactored_code || '';
  const docSections = useMemo(
    () => (report.summary_text ? parseReportDoc(report.summary_text) : []),
    [report.summary_text]
  );

  const copyRefactored = () => {
    navigator.clipboard.writeText(refactoredCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-5">
      {/* Scores */}
      <div className="bg-brand-surface border border-brand-line rounded-lg p-5">
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-[13px] font-semibold text-zinc-900">Audit results</h2>
          <span className="text-[11px] font-mono text-zinc-400">{report.language}</span>
        </div>

        <div className="grid sm:grid-cols-2 gap-x-8 gap-y-4">
          <ScoreBar label="Security" value={report.security_score} />
          <ScoreBar label="Maintainability" value={report.maintainability_score} />
        </div>

        <div className="mt-5 pt-4 border-t border-brand-line grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Stat label="Lines" value={ast.total_lines} />
          <Stat label="Functions" value={ast.function_count} />
          <Stat label="Cyclomatic" value={ast.cyclomatic_complexity} />
          <Stat label="Time / Space" value={report.time_complexity ? `${report.time_complexity} · ${report.space_complexity}` : null} mono small />
        </div>
      </div>

      {/* Issues */}
      {issues.length > 0 && (
        <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
          <div className="px-5 h-11 flex items-center justify-between border-b border-brand-line">
            <h2 className="text-[13px] font-semibold text-zinc-900">
              Findings
              <span className="ml-2 text-[11px] font-mono text-zinc-400">{issues.length}</span>
            </h2>
          </div>
          <ul className="divide-y divide-brand-line">
            {issues.map((issue, idx) => {
              const type = (issue.type || 'info').toLowerCase();
              return (
                <li key={idx} className="px-5 py-3.5">
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <span
                      className={`text-[10px] font-mono uppercase tracking-wide border rounded px-1.5 py-0.5 ${
                        TYPE_STYLES[type] || 'border-brand-line bg-brand-raised text-zinc-500'
                      }`}
                    >
                      {type}
                    </span>
                    {issue.line_number != null && (
                      <span className="text-[11px] font-mono text-zinc-400">
                        line {issue.line_number}
                      </span>
                    )}
                  </div>
                  <p className="text-[13px] text-zinc-800 leading-relaxed">{issue.description}</p>
                  {issue.suggestion && (
                    <p className="mt-1 text-xs text-zinc-500 leading-relaxed">
                      <span className="text-brand-accent">→</span> {issue.suggestion}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Refactored code */}
      {refactoredCode && (
        <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
          <div className="px-5 h-11 flex items-center justify-between border-b border-brand-line">
            <h2 className="text-[13px] font-semibold text-zinc-900">Suggested refactor</h2>
            <button
              onClick={copyRefactored}
              className="flex items-center gap-1.5 text-xs font-mono text-zinc-500 hover:text-zinc-800 border border-brand-line hover:border-zinc-600 rounded-md px-2.5 py-1 transition-colors cursor-pointer"
            >
              {copied ? (
                <><Check size={12} className="text-brand-accent" /> copied</>
              ) : (
                <><Copy size={12} /> copy</>
              )}
            </button>
          </div>
          <pre className="p-5 overflow-x-auto text-xs leading-relaxed font-mono text-emerald-800">
            <code>{refactoredCode}</code>
          </pre>
        </div>
      )}

      {/* Full plain-text report (collapsible) */}
      {docSections.length > 0 && (
        <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
          <button
            onClick={() => setShowDoc((v) => !v)}
            className="w-full px-5 h-11 flex items-center justify-between hover:bg-brand-raised transition-colors cursor-pointer"
          >
            <h2 className="text-[13px] font-semibold text-zinc-900">Full report</h2>
            <span className="text-[11px] font-mono text-zinc-500">
              {showDoc ? 'hide −' : 'show +'}
            </span>
          </button>
          {showDoc && (
            <div className="px-5 pb-5 pt-1 space-y-5 max-h-96 overflow-y-auto">
              {docSections.map((sec, i) => (
                <section key={i}>
                  {sec.heading && (
                    <h3 className="text-[10px] font-mono uppercase tracking-widest text-brand-accent mb-2">
                      {sec.heading}
                    </h3>
                  )}
                  <div className="text-[13px] text-zinc-700 whitespace-pre-line leading-relaxed">
                    {sec.body.join('\n')}
                  </div>
                </section>
              ))}
            </div>
          )}
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
