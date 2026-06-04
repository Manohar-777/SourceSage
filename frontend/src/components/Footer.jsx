import './Footer.css';

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner container">
        <div className="footer-brand">
          <span className="footer-logo gradient-text">SourceSage</span>
          <p className="footer-tagline">AI-powered code review &amp; documentation</p>
        </div>

        <div className="footer-links">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
          >
            GitHub
          </a>
          <span className="footer-divider">·</span>
          <a
            href="https://aistudio.google.com"
            target="_blank"
            rel="noopener noreferrer"
            className="footer-link"
          >
            Google AI Studio
          </a>
        </div>

        <div className="footer-meta">
          <p className="footer-built">
            Built with <span className="footer-heart">♥</span> using
            React, FastAPI &amp; Gemini AI
          </p>
          <p className="footer-copy">
            © {new Date().getFullYear()} Manohar Pasupuleti
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
