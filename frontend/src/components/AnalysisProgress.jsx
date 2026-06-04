import './AnalysisProgress.css';

function AnalysisProgress({ progress, fileReviews, issueCount }) {
  const { current, total, currentFile, phase } = progress;
  const percent = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <section className="progress-section container animate-fade-in">
      {/* Main Progress Card */}
      <div className="progress-card glass-card">
        <div className="progress-header">
          <div className="progress-spinner">
            <span className="spinner-ring" />
            <span className="spinner-icon">🔍</span>
          </div>
          <div className="progress-info">
            <h2 className="progress-title">Analyzing Repository</h2>
            <p className="progress-phase">{phase || 'Starting…'}</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="progress-bar-wrap">
          <div className="progress-bar-track">
            <div
              className="progress-bar-fill"
              style={{ width: `${percent}%` }}
            />
            <div className="progress-bar-shimmer" style={{ width: `${percent}%` }} />
          </div>
          <span className="progress-percent">{percent}%</span>
        </div>

        {/* Counters */}
        <div className="progress-counters">
          <div className="counter">
            <span className="counter-value">{current}</span>
            <span className="counter-label">of {total} files</span>
          </div>
          <div className="counter-divider" />
          <div className="counter">
            <span className="counter-value">{fileReviews.length}</span>
            <span className="counter-label">reviewed</span>
          </div>
          <div className="counter-divider" />
          <div className="counter">
            <span className="counter-value issue-count">{issueCount}</span>
            <span className="counter-label">issues found</span>
          </div>
        </div>

        {/* Current File */}
        {currentFile && (
          <div className="current-file">
            <span className="current-file-label">Processing:</span>
            <span className="current-file-path mono">{currentFile}</span>
            <span className="scan-dot" />
          </div>
        )}
      </div>

      {/* Live Feed */}
      {fileReviews.length > 0 && (
        <div className="live-feed">
          <h3 className="live-feed-title">
            <span className="live-dot" />
            Live Results
          </h3>
          <div className="live-feed-list">
            {[...fileReviews].reverse().map((review, i) => (
              <div key={i} className="live-feed-item glass-card animate-slide-in-left">
                <div className="feed-item-header">
                  <span className="feed-file-icon">{getFileIcon(review.language)}</span>
                  <span className="feed-file-path mono">{review.file_path}</span>
                  <ScoreChip score={review.score} />
                </div>
                {review.issues?.length > 0 && (
                  <div className="feed-issue-badges">
                    {getSeverityCounts(review.issues).map(({ severity, count, icon }) => (
                      <span key={severity} className={`feed-badge badge-${severity}`}>
                        {icon} {count} {severity}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ScoreChip({ score }) {
  const level = score >= 80 ? 'good' : score >= 50 ? 'warn' : 'bad';
  return (
    <span className={`score-chip score-chip-${level}`}>
      {Math.round(score)}/100
    </span>
  );
}

function getSeverityCounts(issues) {
  const map = { critical: 0, warning: 0, info: 0 };
  issues.forEach(i => { if (map[i.severity] !== undefined) map[i.severity]++; });
  const icons = { critical: '🔴', warning: '🟡', info: '🔵' };
  return Object.entries(map)
    .filter(([, count]) => count > 0)
    .map(([severity, count]) => ({ severity, count, icon: icons[severity] }));
}

function getFileIcon(language) {
  const icons = {
    python: '🐍', javascript: '🟨', typescript: '🔷',
    java: '☕', go: '🔵', rust: '🦀',
  };
  return icons[language?.toLowerCase()] || '📄';
}

export default AnalysisProgress;
