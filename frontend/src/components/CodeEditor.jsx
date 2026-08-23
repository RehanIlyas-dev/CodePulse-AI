import React, { useState } from 'react';

const SUPPORTED_LANGUAGES = [
  'python', 'javascript', 'typescript', 'rust',
  'go', 'java', 'csharp', 'cpp', 'ruby', 'php',
];

export default function CodeEditor({ onSubmit, isLoading }) {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');

  const lineCount = code ? code.split('\n').length : 0;

  const handleSubmit = () => {
    if (!code.trim() || isLoading) return;
    if (!code.trim()) {
      setError('Please enter some code to analyze.');
      return;
    }
    setError('');
    onSubmit({
      title: title.trim() || `Scan ${new Date().toLocaleString()}`,
      code,
      language,
    });
  };

  const handleKeyDown = (e) => {
    // Ctrl/Cmd + Enter runs the analysis — standard IDE muscle memory
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-3 px-4 h-11 border-b border-brand-line">
        <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          Source
        </span>

        <div className="flex items-center gap-2">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Untitled scan"
            disabled={isLoading}
            className="bg-brand-bg border border-brand-line text-zinc-700 text-xs rounded-md px-2.5 py-1.5 w-36 focus:outline-none focus:border-brand-accent/60 transition-colors placeholder:text-zinc-400"
          />

          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={isLoading}
            className="bg-brand-bg border border-brand-line text-zinc-700 text-xs font-mono rounded-md px-2 py-1.5 focus:outline-none focus:border-brand-accent/60 transition-colors cursor-pointer"
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang} value={lang}>{lang}</option>
            ))}
          </select>

          <button
            onClick={handleSubmit}
            disabled={isLoading || !code.trim()}
            className="bg-brand-accent-strong hover:bg-brand-accent text-white font-semibold text-xs px-3.5 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {isLoading ? 'Running…' : 'Analyze'}
          </button>
        </div>
      </div>

      {/* Editor */}
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={'# Paste your code here\n# ⌘/Ctrl + Enter to analyze'}
        disabled={isLoading}
        spellCheck={false}
        rows={20}
        className="w-full bg-transparent px-4 py-3.5 text-[13px] font-mono text-zinc-800 resize-none focus:outline-none placeholder:text-zinc-400 leading-relaxed"
      />

      {/* Footer strip */}
      <div className="flex items-center justify-between px-4 h-8 border-t border-brand-line text-[11px] font-mono text-zinc-400">
        <span>{lineCount} lines</span>
        <span className="hidden sm:inline">⌘/Ctrl + ↵ to run</span>
      </div>

      {error && (
        <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20 text-red-400 text-xs">
          {error}
        </div>
      )}
    </div>
  );
}
