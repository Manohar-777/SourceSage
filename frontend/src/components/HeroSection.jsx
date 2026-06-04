import { useEffect, useState } from 'react';
import './HeroSection.css';

const FLOATING_SYMBOLS = [
  '{ }', '< />', 'fn()', '[ ]', '# ', '=> ', '&&', '||',
  '===', '...', '/**/', 'npm', 'git', 'def', 'async', 'const',
];

function HeroSection() {
  const [symbols, setSymbols] = useState([]);

  useEffect(() => {
    const generated = FLOATING_SYMBOLS.map((symbol, i) => ({
      id: i,
      text: symbol,
      left: Math.random() * 90 + 5,
      delay: Math.random() * 8,
      duration: 8 + Math.random() * 12,
      size: 0.7 + Math.random() * 0.8,
    }));
    setSymbols(generated);
  }, []);

  return (
    <section className="hero">
      <div className="hero-bg">
        <div className="hero-gradient" />
        <div className="hero-grid" />
        {symbols.map(s => (
          <span
            key={s.id}
            className="floating-symbol mono"
            style={{
              left: `${s.left}%`,
              animationDelay: `${s.delay}s`,
              animationDuration: `${s.duration}s`,
              fontSize: `${s.size}rem`,
            }}
            aria-hidden="true"
          >
            {s.text}
          </span>
        ))}
      </div>

      <div className="hero-content container">
        <h1 className="hero-headline animate-slide-up">
          Review Code.{' '}
          <span className="gradient-text">Generate Docs.</span>
          <br />
          Ship Better.
        </h1>
        <p className="hero-subtitle animate-slide-up" style={{ animationDelay: '0.15s' }}>
          AI-powered static analysis and documentation generation
          <br className="hero-br" />
          for your GitHub repositories.
        </p>

        <div className="hero-features">
          <div className="feature-card glass-card" style={{ animationDelay: '0.2s' }}>
            <span className="feature-icon">🐛</span>
            <h3 className="feature-title">Bug Detection</h3>
            <p className="feature-desc">
              Catch bugs, security issues, and code smells before they reach production.
            </p>
          </div>
          <div className="feature-card glass-card" style={{ animationDelay: '0.35s' }}>
            <span className="feature-icon">📝</span>
            <h3 className="feature-title">Auto Docs</h3>
            <p className="feature-desc">
              Generate comprehensive README and API documentation in seconds.
            </p>
          </div>
          <div className="feature-card glass-card" style={{ animationDelay: '0.5s' }}>
            <span className="feature-icon">⚡</span>
            <h3 className="feature-title">Instant Analysis</h3>
            <p className="feature-desc">
              Real-time streaming results powered by Google Gemini AI.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
