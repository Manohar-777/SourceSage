import { useMemo } from 'react';
import { CATEGORY_ICONS, SEVERITY_COLORS } from '../utils/constants.js';
import './StatsOverview.css';

function StatsOverview({ stats, issues, fileReviews }) {
  // Category breakdown
  const categoryBreakdown = useMemo(() => {
    const map = {};
    issues.forEach(issue => {
      const cat = issue.category || 'other';
      if (!map[cat]) map[cat] = { critical: 0, warning: 0, info: 0, total: 0 };
      if (issue.severity in map[cat]) map[cat][issue.severity]++;
      map[cat].total++;
    });
    return Object.entries(map)
      .sort((a, b) => b[1].total - a[1].total)
      .slice(0, 8);
  }, [issues]);

  // Top problematic files
  const topFiles = useMemo(() => {
    return [...fileReviews]
      .sort((a, b) => a.score - b.score)
      .slice(0, 5);
  }, [fileReviews]);

  // Score distribution
  const scoreDistribution = useMemo(() => {
    const bands = [
      { label: 'Excellent (90-100)', min: 90, max: 100, color: 'var(--success)' },
      { label: 'Good (75-89)',       min: 75, max: 89,  color: 'var(--accent-primary)' },
      { label: 'Fair (50-74)',       min: 50, max: 74,  color: 'var(--warning)' },
      { label: 'Poor (0-49)',        min: 0,  max: 49,  color: 'var(--error)' },
    ];
    return bands.map(b => ({
      ...b,
      count: fileReviews.filter(r => r.score >= b.min && r.score <= b.max).length,
    }));
  }, [fileReviews]);

  const maxCategoryCount = categoryBreakdown.length > 0
    ? Math.max(...categoryBreakdown.map(([, v]) => v.total))
    : 1;

  if (!stats && fileReviews.length === 0) {
    return (
      <div className="stats-empty glass-card animate-fade-in">
        <span className="empty-icon">📊</span>
        <h3>No statistics available</h3>
        <p>Run an analysis to see detailed statistics.</p>
      </div>
    );
  }

  const score = stats?.overallScore ?? stats?.overall_score ?? 0;
  const scoreClass = score >= 80 ? 'excellent' : score >= 60 ? 'good' : score >= 40 ? 'fair' : 'poor';
  const circumference = 2 * Math.PI * 45; // r=45

  return (
    <div className="stats-overview animate-fade-in">

      {/* Top Row — Score + Summary Cards */}
      <div className="stats-top-row">
        {/* Score Dial */}
        <div className="stats-card glass-card score-dial-card">
          <h3 className="stats-card-title">Overall Quality Score</h3>
          <div className="score-dial-wrap">
            <svg className="score-dial-svg" viewBox="0 0 100 100">
              <circle
                cx="50" cy="50" r="45"
                fill="none"
                stroke="var(--border)"
                strokeWidth="8"
              />
              <circle
                cx="50" cy="50" r="45"
                fill="none"
                stroke={SEVERITY_COLORS.info}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${(score / 100) * circumference} ${circumference}`}
                strokeDashoffset={circumference / 4}
                className="dial-progress"
                style={{ stroke: scoreColor(score) }}
              />
            </svg>
            <div className="score-dial-inner">
              <span className={`score-dial-value ${scoreClass}`}>{Math.round(score)}</span>
              <span className="score-dial-label">/ 100</span>
            </div>
          </div>
          <p className={`score-quality-label quality-${scoreClass}`}>
            {scoreClass.charAt(0).toUpperCase() + scoreClass.slice(1)} Quality
          </p>
          {stats?.summary && (
            <p className="score-summary">{stats.summary}</p>
          )}
        </div>

        {/* Issue Counts */}
        <div className="stats-issue-cards">
          <StatBigCard
            icon="🔴"
            value={stats?.criticalCount ?? issues.filter(i => i.severity === 'critical').length}
            label="Critical"
            color="var(--error)"
            glow="var(--error-glow)"
          />
          <StatBigCard
            icon="🟡"
            value={stats?.warningCount ?? issues.filter(i => i.severity === 'warning').length}
            label="Warnings"
            color="var(--warning)"
            glow="var(--warning-glow)"
          />
          <StatBigCard
            icon="🔵"
            value={stats?.infoCount ?? issues.filter(i => i.severity === 'info').length}
            label="Info"
            color="var(--accent-primary)"
            glow="var(--accent-glow)"
          />
          <StatBigCard
            icon="📁"
            value={stats?.filesScanned ?? fileReviews.length}
            label="Files Scanned"
            color="var(--text-secondary)"
            glow="var(--bg-tertiary)"
          />
        </div>
      </div>

      {/* Score Distribution */}
      {fileReviews.length > 1 && (
        <div className="stats-card glass-card">
          <h3 className="stats-card-title">Score Distribution</h3>
          <div className="score-dist-grid">
            {scoreDistribution.map(({ label, count, color }) => (
              <div key={label} className="score-dist-row">
                <span className="dist-label">{label}</span>
                <div className="dist-bar-track">
                  <div
                    className="dist-bar-fill"
                    style={{
                      width: fileReviews.length > 0 ? `${(count / fileReviews.length) * 100}%` : '0%',
                      background: color,
                    }}
                  />
                </div>
                <span className="dist-count">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Two column: categories + top files */}
      <div className="stats-bottom-row">
        {/* Category Breakdown */}
        {categoryBreakdown.length > 0 && (
          <div className="stats-card glass-card">
            <h3 className="stats-card-title">Issues by Category</h3>
            <div className="category-list">
              {categoryBreakdown.map(([cat, counts]) => (
                <div key={cat} className="category-row">
                  <span className="cat-icon">{CATEGORY_ICONS[cat] || '📌'}</span>
                  <span className="cat-name">{cat}</span>
                  <div className="cat-bar-track">
                    <div
                      className="cat-bar-fill"
                      style={{ width: `${(counts.total / maxCategoryCount) * 100}%` }}
                    />
                  </div>
                  <div className="cat-badges">
                    {counts.critical > 0 && (
                      <span className="cat-badge critical">{counts.critical}</span>
                    )}
                    {counts.warning > 0 && (
                      <span className="cat-badge warning">{counts.warning}</span>
                    )}
                    {counts.info > 0 && (
                      <span className="cat-badge info">{counts.info}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Files Needing Attention */}
        {topFiles.length > 0 && (
          <div className="stats-card glass-card">
            <h3 className="stats-card-title">Files Needing Attention</h3>
            <div className="top-files-list">
              {topFiles.map((review, i) => (
                <div key={i} className="top-file-row">
                  <span className="top-file-rank">#{i + 1}</span>
                  <div className="top-file-info">
                    <span className="top-file-path mono">{review.file_path}</span>
                    {review.summary && (
                      <span className="top-file-summary">{review.summary.slice(0, 80)}…</span>
                    )}
                  </div>
                  <ScoreRing score={review.score} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatBigCard({ icon, value, label, color, glow }) {
  return (
    <div
      className="stat-big-card glass-card"
      style={{ '--card-color': color, '--card-glow': glow }}
    >
      <span className="stat-big-icon">{icon}</span>
      <span className="stat-big-value">{value}</span>
      <span className="stat-big-label">{label}</span>
    </div>
  );
}

function ScoreRing({ score }) {
  const cls = score >= 80 ? 'good' : score >= 50 ? 'warn' : 'bad';
  return (
    <span className={`score-ring score-ring-${cls}`}>{Math.round(score)}</span>
  );
}

function scoreColor(score) {
  if (score >= 80) return 'var(--success)';
  if (score >= 60) return 'var(--accent-primary)';
  if (score >= 40) return 'var(--warning)';
  return 'var(--error)';
}

export default StatsOverview;
