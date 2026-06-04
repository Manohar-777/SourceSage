import { useTheme } from '../contexts/ThemeContext.jsx';
import './Header.css';

function Header({ apiKey }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="header glass">
      <div className="header-inner container">
        <div className="header-brand">
          <div className="header-logo" aria-hidden="true">
            <span className="logo-bracket">{'{'}</span>
            <span className="logo-dot">·</span>
            <span className="logo-bracket">{'}'}</span>
          </div>
          <div className="header-titles">
            <h1 className="header-title">
              Source<span className="gradient-text">Sage</span>
            </h1>
            <p className="header-subtitle">AI-Powered Code Review & Docs</p>
          </div>
        </div>

        <div className="header-actions">
          <div className="api-status" title={apiKey ? 'API key is set' : 'API key not set'}>
            <span className={`status-dot ${apiKey ? 'connected' : 'disconnected'}`} />
            <span className="status-label">{apiKey ? 'API Ready' : 'No API Key'}</span>
          </div>

          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          >
            <span className={`theme-icon ${theme === 'dark' ? 'moon' : 'sun'}`}>
              {theme === 'dark' ? '🌙' : '☀️'}
            </span>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
