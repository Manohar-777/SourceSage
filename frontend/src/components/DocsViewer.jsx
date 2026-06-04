import { useState } from 'react';
import './DocsViewer.css';

function DocsViewer({ docs, onGenerateDocs, repoUrl }) {
  const [activeFile, setActiveFile] = useState(null);
  const [copied, setCopied] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      await onGenerateDocs();
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(''), 2000);
    } catch {
      // fallback
    }
  };

  if (!docs) {
    return (
      <div className="docs-generate-screen glass-card animate-fade-in">
        <div className="docs-generate-icon">📝</div>
        <h3>Generate Documentation</h3>
        <p>
          SourceSage will use Gemini AI to generate a comprehensive README and
          per-file documentation for <strong>{repoUrl}</strong>.
        </p>
        <ul className="docs-feature-list">
          <li><span>📄</span> Professional README.md</li>
          <li><span>🔧</span> Per-file API documentation</li>
          <li><span>📐</span> Function &amp; class descriptions</li>
          <li><span>💡</span> Usage examples</li>
        </ul>
        <button
          className="btn btn-primary docs-generate-btn"
          onClick={handleGenerate}
          disabled={isGenerating}
        >
          {isGenerating ? (
            <>
              <span className="btn-spinner" />
              Generating…
            </>
          ) : (
            <>
              <span>✨</span>
              Generate Documentation
            </>
          )}
        </button>
      </div>
    );
  }

  const filePaths = Object.keys(docs.file_docs || {});
  const currentFile = activeFile || (filePaths.length > 0 ? filePaths[0] : null);
  const currentDoc = currentFile ? docs.file_docs[currentFile] : null;

  return (
    <div className="docs-viewer animate-fade-in">
      {/* Sidebar */}
      <nav className="docs-sidebar glass-card">
        <div className="docs-sidebar-header">
          <span className="sidebar-icon">📚</span>
          <h3>Documentation</h3>
        </div>

        {/* README entry */}
        <button
          className={`docs-nav-item ${activeFile === null ? 'active' : ''}`}
          onClick={() => setActiveFile(null)}
        >
          <span className="nav-icon">📋</span>
          <span>README.md</span>
        </button>

        {filePaths.length > 0 && (
          <>
            <div className="docs-nav-divider">
              <span>Source Files</span>
            </div>
            {filePaths.map((fp) => (
              <button
                key={fp}
                className={`docs-nav-item ${activeFile === fp ? 'active' : ''}`}
                onClick={() => setActiveFile(fp)}
                title={fp}
              >
                <span className="nav-icon">{getFileIcon(fp)}</span>
                <span className="nav-label mono">{fp.split('/').pop()}</span>
              </button>
            ))}
          </>
        )}

        <div className="docs-sidebar-footer">
          <button
            className="btn btn-secondary docs-regen-btn"
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating ? (
              <><span className="btn-spinner-sm" />Regenerating…</>
            ) : (
              <><span>🔄</span> Regenerate</>
            )}
          </button>
        </div>
      </nav>

      {/* Content Pane */}
      <div className="docs-content glass-card">
        <div className="docs-content-header">
          <h4 className="docs-content-title">
            {activeFile === null ? '📋 README.md' : `📄 ${activeFile}`}
          </h4>
          <button
            className="docs-copy-btn"
            onClick={() => handleCopy(
              activeFile === null ? (docs.readme_content || '') : (currentDoc || ''),
              activeFile || 'readme'
            )}
          >
            {copied === (activeFile || 'readme') ? (
              <><span>✓</span> Copied!</>
            ) : (
              <><span>📋</span> Copy</>
            )}
          </button>
        </div>

        <div className="docs-content-body">
          {activeFile === null ? (
            <MarkdownView content={docs.readme_content || '_No README generated._'} />
          ) : currentDoc ? (
            <MarkdownView content={currentDoc} />
          ) : (
            <p className="docs-empty">No documentation generated for this file.</p>
          )}
        </div>
      </div>
    </div>
  );
}

/** Renders markdown-like content as styled preformatted text */
function MarkdownView({ content }) {
  // Simple renderer: render code blocks specially, rest as paragraphs
  const lines = content.split('\n');
  const rendered = [];
  let inCode = false;
  let codeBlock = [];
  let codeLang = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('```')) {
      if (!inCode) {
        inCode = true;
        codeLang = line.slice(3).trim();
        codeBlock = [];
      } else {
        rendered.push(
          <pre key={i} className="md-code-block">
            {codeLang && <span className="md-code-lang">{codeLang}</span>}
            <code>{codeBlock.join('\n')}</code>
          </pre>
        );
        inCode = false;
        codeBlock = [];
      }
    } else if (inCode) {
      codeBlock.push(line);
    } else if (line.startsWith('# ')) {
      rendered.push(<h1 key={i} className="md-h1">{line.slice(2)}</h1>);
    } else if (line.startsWith('## ')) {
      rendered.push(<h2 key={i} className="md-h2">{line.slice(3)}</h2>);
    } else if (line.startsWith('### ')) {
      rendered.push(<h3 key={i} className="md-h3">{line.slice(4)}</h3>);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      rendered.push(<li key={i} className="md-li">{line.slice(2)}</li>);
    } else if (line.trim() === '') {
      rendered.push(<div key={i} className="md-spacer" />);
    } else {
      rendered.push(<p key={i} className="md-p">{line}</p>);
    }
  }

  return <div className="md-view">{rendered}</div>;
}

function getFileIcon(path) {
  const ext = path.split('.').pop();
  const icons = {
    py: '🐍', js: '🟨', ts: '🔷', jsx: '🟨',
    tsx: '🔷', java: '☕', go: '🔵', rs: '🦀',
  };
  return icons[ext] || '📄';
}

export default DocsViewer;
