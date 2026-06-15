import { useState, useEffect } from 'react';
import './RepoInput.css';

function RepoInput({ onAnalyze, isLoading, errorMessage, apiKey, onApiKeyChange }) {
  const [url, setUrl] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [recentRepos, setRecentRepos] = useState([]);
  const [showRecent, setShowRecent] = useState(false);
  const [branch, setBranch] = useState('');

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('sourcesage-recent-repos') || '[]');
      setRecentRepos(stored);
    } catch {
      // ignore
    }
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) {
      onAnalyze(url.trim(), branch.trim() || null);
    }
  };

  const isValidUrl = (value) => {
    try {
      const parsed = new URL(value);
      return parsed.hostname === 'github.com' && parsed.pathname.split('/').filter(Boolean).length >= 2;
    } catch {
      return false;
    }
  };

  const urlValid = url.trim() === '' || isValidUrl(url.trim());

  return (
    <section className="repo-input-section container animate-fade-in">
      {/* Settings Panel */}
      <div className={`settings-panel glass-card ${showSettings ? 'open' : ''}`}>
        <button
          className="settings-toggle"
          onClick={() => setShowSettings(!showSettings)}
          aria-expanded={showSettings}
          aria-label="Toggle API settings"
        >
          <span className="settings-icon">⚙️</span>
          <span>API Settings</span>
          <span className={`settings-chevron ${showSettings ? 'rotated' : ''}`}>▾</span>
        </button>

        {showSettings && (
          <div className="settings-body">
            <label className="settings-label" htmlFor="api-key-input">
              <span className="label-icon">🔑</span>
              Google Gemini API Key
            </label>
            <div className="api-key-row">
              <input
                id="api-key-input"
                type="password"
                className="input api-key-input"
                placeholder="Enter your Gemini API key..."
                value={apiKey}
                onChange={(e) => onApiKeyChange(e.target.value)}
                autoComplete="off"
              />
              {apiKey && (
                <span className="api-key-check" title="API key is set">✓</span>
              )}
            </div>
            <p className="settings-hint">
              Get your API key from{' '}
              <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">
                Google AI Studio
              </a>
            </p>
          </div>
        )}
      </div>

      {/* Main Input */}
      <form className="repo-form glass-card" onSubmit={handleSubmit}>
        <div className="input-group">
          <div className="input-icon-wrapper">
            <span className="input-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path fillRule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
              </svg>
            </span>
            <input
              type="url"
              className={`input repo-url-input ${!urlValid ? 'invalid' : ''}`}
              placeholder="https://github.com/owner/repository"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onFocus={() => recentRepos.length > 0 && setShowRecent(true)}
              onBlur={() => setTimeout(() => setShowRecent(false), 200)}
              disabled={isLoading}
              required
              id="repo-url-input"
            />
          </div>

          <input
            type="text"
            className="input repo-branch-input"
            placeholder="branch (optional)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            disabled={isLoading}
            autoComplete="off"
          />

          <button
            type="submit"
            className="btn btn-primary analyze-btn"
            disabled={isLoading || !url.trim() || !urlValid || !apiKey}
          >
            {isLoading ? (
              <>
                <span className="btn-spinner" />
                Analyzing...
              </>
            ) : (
              <>
                <span className="btn-icon">🔍</span>
                Analyze
              </>
            )}
          </button>
        </div>

        {!urlValid && url.trim() && (
          <p className="input-error">Please enter a valid GitHub repository URL</p>
        )}

        {errorMessage && (
          <div className="error-message animate-shake">
            <span className="error-icon">⚠️</span>
            <p>{errorMessage}</p>
          </div>
        )}

        {/* Recent Repos Dropdown */}
        {showRecent && recentRepos.length > 0 && (
          <div className="recent-repos">
            <p className="recent-label">Recent repositories</p>
            {recentRepos.map((repo, i) => (
              <button
                key={i}
                type="button"
                className="recent-item"
                onMouseDown={() => {
                  setUrl(repo);
                  setShowRecent(false);
                }}
              >
                <span className="recent-icon">📁</span>
                <span className="recent-url">{repo}</span>
              </button>
            ))}
          </div>
        )}
      </form>

      {!apiKey && (
        <p className="api-key-hint animate-fade-in">
          <span className="hint-icon">💡</span>
          Set your Gemini API key in <button className="link-btn" onClick={() => setShowSettings(true)}>API Settings</button> to get started
        </p>
      )}
    </section>
  );
}

export default RepoInput;
