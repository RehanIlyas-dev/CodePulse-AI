import React from 'react';

const STAGES = ['Queued', 'Static parse', 'AI audit', 'Report'];

function stageFor(status) {
  switch (status) {
    case 'PENDING': return 0;
    case 'PARSING_AST':
    case 'PARSING_FILES': return 1;
    case 'BUILDING_DEPENDENCY_GRAPH':
    case 'RUNNING_AI_AUDIT': return 2;
    case 'COMPLETED':
    case 'CACHE_HIT': return 3;
    default: return 0;
  }
}

const DONE = new Set(['COMPLETED', 'CACHE_HIT']);

export default function JobProgress({ status, progress, error }) {
  const failed = status === 'FAILED' || !!error;
  const done = DONE.has(status);
  const currentStep = stageFor(status);

  return (
    <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
      {/* Stepper */}
      <div className="px-5 py-4">
        <div className="flex items-center">
          {STAGES.map((label, i) => {
            const reached = !failed && i <= currentStep;
            const active = !failed && !done && i === currentStep;
            return (
              <React.Fragment key={label}>
                {i > 0 && (
                  <div
                    className={`flex-1 h-px mx-2 ${
                      failed ? 'bg-red-500/30' : reached ? 'bg-brand-accent/60' : 'bg-brand-line'
                    }`}
                  />
                )}
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-mono ${
                      failed
                        ? i <= currentStep ? 'border-red-500 text-red-400' : 'border-brand-line text-zinc-400'
                        : done
                        ? 'bg-brand-accent-strong border-brand-accent-strong text-white'
                        : active
                        ? 'border-brand-accent text-brand-accent'
                        : reached
                        ? 'border-brand-accent/50 text-brand-accent/70'
                        : 'border-brand-line text-zinc-400'
                    }`}
                  >
                    {done && i === 3 ? '✓' : i + 1}
                  </span>
                  <span
                    className={`text-xs hidden sm:block ${
                      failed
                        ? i <= currentStep ? 'text-red-400' : 'text-zinc-400'
                        : done || active
                        ? 'text-zinc-800'
                        : reached
                        ? 'text-zinc-500'
                        : 'text-zinc-400'
                    }`}
                  >
                    {failed && status === 'FAILED' ? 'Failed' : label}
                  </span>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Detail strip */}
      <div
        className={`px-5 py-2.5 border-t flex items-center justify-between gap-3 ${
          failed ? 'bg-red-500/10 border-red-500/20' : 'bg-brand-bg border-brand-line'
        }`}
      >
        {failed ? (
          <p className="text-xs text-red-400 truncate" title={error || ''}>
            {error || 'An unexpected error occurred during processing.'}
          </p>
        ) : (
          <>
            <p className="text-xs font-mono text-zinc-500">
              {status === 'CACHE_HIT' ? 'Served from cache' : `${status.toLowerCase()}…`}
              <span className="animate-pulse">▍</span>
            </p>
            <p className="text-xs font-mono text-zinc-500 tabular-nums">{progress}%</p>
          </>
        )}
      </div>
    </div>
  );
}
