import { useState, useMemo } from 'react';
import { SEVERITY_COLORS, SEVERITY_LABELS, SEVERITY_ORDER, CATEGORY_ICONS } from '../utils/constants.js';
import './ReviewPanel.css';

function ReviewPanel({ fileReviews, issues }) {
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedFiles, setExpandedFiles] = useState(new Set());
  const [sortBy, setSortBy] = useState('severity'); // 'severity' | 'file' | 'score'

  // Unique categories across all issues
  const categories = useMemo(() => {
    const cats = new Set(issues.map(i => i.category).filter(Boolean));
    return ['all', ...Array.from(cats).sort()];
  }, [issues]);

  // Filtered & sorted issues
  const filteredIssues = useMemo(() => {
    let list = [...issues];
    if (filterSeverity !== 'all') list = list.filter(i => i.severity === filterSeverity);
    if (filterCategory !== 'all') list = list.filter(i => i.category === filterCategory);
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      list = list.filter(i =>
        (i.description || '').toLowerCase().includes(q) ||
        (i.file_path || '').toLowerCase().includes(q) ||
        (i.category || '').toLowerCase().includes(q)
      );
    }
    if (sortBy === 'severity') {
      list.sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99));
    } else if (sortBy === 'file') {
      list.sort((a, b) => (a.file_path || '').localeCompare(b.file_path || ''));
    }
    return list;
  }, [issues, filterSeverity, filterCategory, searchTerm, sortBy]);

  // Group issues by file
  const byFile = useMemo(() => {
    const map = new Map();
    filteredIssues.forEach(issue => {
      const key = issue.file_path || 'Unknown file';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(issue);
    });
    return map;
  }, [filteredIssues]);

  const toggleFile = (fp) => {
    setExpandedFiles(prev => {
      const next = new Set(prev);
      next.has(fp) ? next.delete(fp) : next.add(fp);
      return next;
    });
  };

  const severityCount = (s) => issues.filter(i => i.severity === s).length;

  if (issues.length === 0 && fileReviews.length === 0) {
    return (
      <div className="review-empty glass-card animate-fade-in">
        <span className="empty-icon">✅</span>
        <h3>No issues found</h3>
        <p>The repository looks clean! No issues were detected during analysis.</p>
      </div>
    );
  }

  return (
    <div className="review-panel animate-fade-in">
      {/* Summary Chips */}
      <div className="severity-summary">
        {['critical', 'warning', 'info'].map(s => (
          <button
            key={s}
            className={`severity-chip ${filterSeverity === s ? 'active' : ''}`}
            style={{ '--chip-color': SEVERITY_COLORS[s] }}
            onClick={() => setFilterSeverity(prev => prev === s ? 'all' : s)}
          >
            <span className="chip-dot" />
            <span>{severityCount(s)}</span>
            <span>{SEVERITY_LABELS[s]}</span>
          </button>
        ))}
        {filterSeverity !== 'all' && (
          <button className="chip-clear" onClick={() => setFilterSeverity('all')}>
            ✕ Clear filter
          </button>
        )}
      </div>

      {/* Filters Row */}
      <div className="review-filters glass-card">
        <div className="filter-search">
          <span className="filter-search-icon">🔎</span>
          <input
            type="text"
            className="input filter-input"
            placeholder="Search issues, files, categories…"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-selects">
          <select
            className="filter-select"
            value={filterCategory}
            onChange={e => setFilterCategory(e.target.value)}
          >
            {categories.map(c => (
              <option key={c} value={c}>
                {c === 'all' ? 'All categories' : `${CATEGORY_ICONS[c] || '📌'} ${c}`}
              </option>
            ))}
          </select>

          <select
            className="filter-select"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="severity">Sort: Severity</option>
            <option value="file">Sort: File</option>
          </select>
        </div>
      </div>

      {/* Results count */}
      <p className="review-count">
        Showing <strong>{filteredIssues.length}</strong> of <strong>{issues.length}</strong> issues
        across <strong>{fileReviews.length}</strong> files
      </p>

      {/* Issues grouped by file */}
      {filteredIssues.length === 0 ? (
        <div className="review-empty glass-card">
          <span className="empty-icon">🔍</span>
          <h3>No matching issues</h3>
          <p>Try adjusting your filters or search term.</p>
        </div>
      ) : (
        <div className="file-groups">
          {Array.from(byFile.entries()).map(([filePath, fileIssues]) => {
            const isExpanded = expandedFiles.has(filePath) || byFile.size === 1;
            const fileReview = fileReviews.find(r => r.file_path === filePath);
            return (
              <div key={filePath} className="file-group glass-card">
                <button
                  className="file-group-header"
                  onClick={() => toggleFile(filePath)}
                  aria-expanded={isExpanded}
                >
                  <span className="file-lang-icon">
                    {getFileIcon(fileReview?.language)}
                  </span>
                  <span className="file-path mono">{filePath}</span>
                  <div className="file-group-meta">
                    {fileReview && (
                      <span className={`file-score ${getScoreClass(fileReview.score)}`}>
                        {Math.round(fileReview.score)}/100
                      </span>
                    )}
                    <span className="file-issue-count">
                      {fileIssues.length} issue{fileIssues.length !== 1 ? 's' : ''}
                    </span>
                    <span className={`file-chevron ${isExpanded ? 'open' : ''}`}>▾</span>
                  </div>
                </button>

                {fileReview?.summary && (
                  <p className="file-summary">{fileReview.summary}</p>
                )}

                {isExpanded && (
                  <div className="issue-list">
                    {fileIssues.map((issue, idx) => (
                      <IssueCard key={idx} issue={issue} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function IssueCard({ issue }) {
  const [expanded, setExpanded] = useState(false);
  const color = SEVERITY_COLORS[issue.severity] || 'var(--text-muted)';
  const icon = CATEGORY_ICONS[issue.category] || '📌';

  return (
    <div className="issue-card" style={{ '--issue-color': color }}>
      <div className="issue-header" onClick={() => setExpanded(e => !e)}>
        <span className={`issue-severity-bar severity-${issue.severity}`} />
        <span className="issue-category-icon">{icon}</span>
        <div className="issue-title-wrap">
          <span className={`issue-severity-badge badge-${issue.severity}`}>
            {SEVERITY_LABELS[issue.severity] || issue.severity}
          </span>
          <span className="issue-category">{issue.category}</span>
          {issue.line_number && (
            <span className="issue-line mono">L{issue.line_number}</span>
          )}
        </div>
        <span className={`issue-chevron ${expanded ? 'open' : ''}`}>▾</span>
      </div>

      <p className="issue-description">{issue.description}</p>

      {expanded && (
        <div className="issue-details animate-fade-in">
          {issue.suggestion && (
            <div className="issue-suggestion">
              <span className="suggestion-icon">💡</span>
              <p>{issue.suggestion}</p>
            </div>
          )}
          {issue.code_snippet && (
            <pre className="issue-snippet mono"><code>{issue.code_snippet}</code></pre>
          )}
        </div>
      )}
    </div>
  );
}

function getFileIcon(language) {
  const icons = {
    python: '🐍', javascript: '🟨', typescript: '🔷',
    java: '☕', go: '🔵', rust: '🦀',
  };
  return icons[language?.toLowerCase()] || '📄';
}

function getScoreClass(score) {
  if (score >= 80) return 'score-good';
  if (score >= 50) return 'score-warn';
  return 'score-bad';
}

export default ReviewPanel;
