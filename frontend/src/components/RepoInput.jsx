import React, { useRef, useState } from 'react';
import { GitBranch, UploadCloud, FileArchive, X } from 'lucide-react';

const MAX_ZIP_MB = 10;

export default function RepoInput({ onSubmit, isLoading }) {
  const [githubUrl, setGithubUrl] = useState('');
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  const acceptFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.zip')) {
      setError('Only .zip archives are accepted.');
      return;
    }
    if (f.size > MAX_ZIP_MB * 1024 * 1024) {
      setError(`File exceeds the ${MAX_ZIP_MB} MB limit.`);
      return;
    }
    setError('');
    setGithubUrl('');
    setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleSubmit = () => {
    if (isLoading) return;
    if (!githubUrl.trim() && !file) {
      setError('Enter a GitHub URL or attach a .zip archive.');
      return;
    }
    if (githubUrl.trim() && file) {
      setError('Choose one input: URL or zip, not both.');
      return;
    }
    onSubmit({ githubUrl: githubUrl.trim(), file });
  };

  return (
    <div className="bg-brand-surface border border-brand-line rounded-lg overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 h-11 border-b border-brand-line">
        <span className="text-[11px] font-mono uppercase tracking-wider text-zinc-500">
          Repository
        </span>
        <button
          onClick={handleSubmit}
          disabled={isLoading || (!githubUrl.trim() && !file)}
          className="bg-brand-accent-strong hover:bg-brand-accent text-white font-semibold text-xs px-3.5 py-1.5 rounded-md transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {isLoading ? 'Running…' : 'Analyze repo'}
        </button>
      </div>

      <div className="p-4 space-y-3">
        {/* GitHub URL */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 flex-1 bg-brand-bg border border-brand-line rounded-md px-2.5 focus-within:border-brand-accent/60 transition-colors">
            <GitBranch size={14} className="text-zinc-400 shrink-0" />
            <input
              type="text"
              value={githubUrl}
              onChange={(e) => { setGithubUrl(e.target.value); if (e.target.value) setFile(null); }}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
              placeholder="https://github.com/user/repo"
              disabled={isLoading}
              spellCheck={false}
              className="w-full bg-transparent text-[13px] font-mono text-zinc-800 py-2 focus:outline-none placeholder:text-zinc-400"
            />
          </div>
        </div>

        <div className="flex items-center gap-3" aria-hidden>
          <div className="h-px flex-1 bg-brand-line" />
          <span className="text-[10px] font-mono uppercase tracking-widest text-zinc-400">or</span>
          <div className="h-px flex-1 bg-brand-line" />
        </div>

        {/* Drop zone */}
        {file ? (
          <div className="flex items-center justify-between bg-brand-bg border border-brand-line rounded-md px-3 py-2.5">
            <div className="flex items-center gap-2.5 min-w-0">
              <FileArchive size={16} className="text-brand-accent shrink-0" />
              <div className="min-w-0 leading-tight">
                <p className="text-xs font-mono text-zinc-700 truncate">{file.name}</p>
                <p className="text-[10px] font-mono text-zinc-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={() => setFile(null)}
              disabled={isLoading}
              className="text-zinc-400 hover:text-red-500 transition-colors cursor-pointer p-1"
              aria-label="Remove file"
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => !isLoading && fileInputRef.current?.click()}
            className={`border border-dashed rounded-md px-4 py-6 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-brand-accent bg-brand-accent/5'
                : 'border-brand-line hover:border-zinc-300 hover:bg-brand-raised'
            }`}
          >
            <UploadCloud size={18} className="mx-auto text-zinc-400 mb-1.5" />
            <p className="text-xs text-zinc-500">
              Drop a <span className="font-mono">.zip</span> here or click to browse
            </p>
            <p className="text-[10px] font-mono text-zinc-400 mt-1">max {MAX_ZIP_MB} MB</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip"
              hidden
              onChange={(e) => acceptFile(e.target.files?.[0])}
            />
          </div>
        )}

        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}
      </div>
    </div>
  );
}
