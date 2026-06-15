import { useState, useCallback, useEffect } from 'react';
import { ThemeProvider } from './contexts/ThemeContext.jsx';
import Header from './components/Header.jsx';
import HeroSection from './components/HeroSection.jsx';
import RepoInput from './components/RepoInput.jsx';
import AnalysisProgress from './components/AnalysisProgress.jsx';
import ReviewPanel from './components/ReviewPanel.jsx';
import DocsViewer from './components/DocsViewer.jsx';
import StatsOverview from './components/StatsOverview.jsx';
import Footer from './components/Footer.jsx';
import { analyzeRepo, generateDocs } from './utils/api.js';
import { ANALYSIS_STATES, MAX_RECENT_REPOS } from './utils/constants.js';
import './App.css';

function AppContent() {
  const [analysisState, setAnalysisState] = useState(ANALYSIS_STATES.IDLE);
  const [analysisData, setAnalysisData] = useState({
    report: null,
    fileReviews: [],
    progress: { current: 0, total: 0, currentFile: '', phase: '' },
    issues: [],
    stats: null,
    docs: null,
  });
  const [activeTab, setActiveTab] = useState('review');
  const [apiKey, setApiKey] = useState(() => {
    try {
      return localStorage.getItem('sourcesage-api-key') || '';
    } catch {
      return '';
    }
  });
  const [repoUrl, setRepoUrl] = useState('');
  const [branchName, setBranchName] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Persist API key
  useEffect(() => {
    try {
      if (apiKey) {
        localStorage.setItem('sourcesage-api-key', apiKey);
      }
    } catch {
      // localStorage unavailable
    }
  }, [apiKey]);

  const addRecentRepo = useCallback((url) => {
    try {
      const stored = JSON.parse(localStorage.getItem('sourcesage-recent-repos') || '[]');
      const filtered = stored.filter(r => r !== url);
      filtered.unshift(url);
      localStorage.setItem(
        'sourcesage-recent-repos',
        JSON.stringify(filtered.slice(0, MAX_RECENT_REPOS))
      );
    } catch {
      // ignore
    }
  }, []);

  const handleAnalyze = useCallback(async (url, branch = null) => {
    if (!url) return;
    if (!apiKey) {
      setErrorMessage('Please set your Gemini API key first (click the ⚙️ button).');
      return;
    }

    setRepoUrl(url);
    setBranchName(branch || '');
    setErrorMessage('');
    setAnalysisState(ANALYSIS_STATES.CLONING);
    setAnalysisData({
      report: null,
      fileReviews: [],
      progress: { current: 0, total: 0, currentFile: '', phase: 'Cloning repository...' },
      issues: [],
      stats: null,
      docs: null,
    });

    addRecentRepo(url);

    let fileIndex = 0;

    await analyzeRepo(url, branch, apiKey, (event) => {
      switch (event.type) {
        // ── Backend SSE event: clone_start ──
        case 'clone_start':
          setAnalysisState(ANALYSIS_STATES.CLONING);
          setAnalysisData(prev => ({
            ...prev,
            progress: { ...prev.progress, phase: 'Cloning repository...' },
          }));
          break;

        // ── Backend SSE event: clone_complete ──
        case 'clone_complete':
          setAnalysisState(ANALYSIS_STATES.ANALYZING);
          setAnalysisData(prev => ({
            ...prev,
            progress: {
              current: 0,
              total: event.data?.files || 0,
              currentFile: '',
              phase: `Found ${event.data?.files || 0} source files. Starting analysis...`,
            },
          }));
          break;

        // ── Backend SSE event: file_start ──
        case 'file_start':
          fileIndex++;
          setAnalysisData(prev => ({
            ...prev,
            progress: {
              ...prev.progress,
              current: fileIndex,
              currentFile: event.data?.file || '',
              phase: `Analyzing file ${fileIndex} of ${prev.progress.total}...`,
            },
          }));
          break;

        // ── Backend SSE event: file_skip ──
        case 'file_skip':
          setAnalysisData(prev => ({
            ...prev,
            progress: {
              ...prev.progress,
              phase: `Skipped ${event.data?.file || 'file'}: ${event.data?.reason || 'too large'}`,
            },
          }));
          break;

        // ── Backend SSE event: file_complete ──
        case 'file_complete': {
          const review = event.data?.review;
          if (review) {
            setAnalysisData(prev => {
              const newIssues = (review.issues || []).map(issue => ({
                ...issue,
                file_path: issue.file_path || review.file_path,
              }));
              return {
                ...prev,
                fileReviews: [...prev.fileReviews, review],
                issues: [...prev.issues, ...newIssues],
              };
            });
          }
          break;
        }

        // ── Backend SSE event: analysis_complete ──
        case 'analysis_complete':
          setAnalysisState(ANALYSIS_STATES.COMPLETE);
          setAnalysisData(prev => ({
            ...prev,
            report: event.data?.report || null,
            stats: event.data?.report ? {
              filesScanned: event.data.report.total_files,
              filesAnalyzed: event.data.report.files_analyzed,
              overallScore: event.data.report.overall_score,
              criticalCount: event.data.report.critical_count,
              warningCount: event.data.report.warning_count,
              infoCount: event.data.report.info_count,
              summary: event.data.report.summary,
            } : prev.stats,
          }));
          break;

        // ── Stream ended ──
        case 'done':
          setAnalysisData(prev => {
            if (analysisState !== ANALYSIS_STATES.COMPLETE && prev.fileReviews.length > 0) {
              // If we got reviews but no analysis_complete event
              return {
                ...prev,
                stats: prev.stats || {
                  filesScanned: prev.fileReviews.length,
                  filesAnalyzed: prev.fileReviews.length,
                  overallScore: prev.fileReviews.length > 0
                    ? Math.round(prev.fileReviews.reduce((sum, r) => sum + (r.score || 0), 0) / prev.fileReviews.length)
                    : 0,
                  criticalCount: prev.issues.filter(i => i.severity === 'critical').length,
                  warningCount: prev.issues.filter(i => i.severity === 'warning').length,
                  infoCount: prev.issues.filter(i => i.severity === 'info').length,
                  summary: `Analyzed ${prev.fileReviews.length} files.`,
                },
              };
            }
            return prev;
          });
          // If still in analyzing state when done fires, mark complete
          setAnalysisState(prev =>
            prev === ANALYSIS_STATES.ANALYZING || prev === ANALYSIS_STATES.CLONING
              ? ANALYSIS_STATES.COMPLETE
              : prev
          );
          break;

        // ── Error ──
        case 'error':
          setAnalysisState(ANALYSIS_STATES.ERROR);
          setErrorMessage(event.data?.message || 'Analysis failed. Please try again.');
          break;

        default:
          break;
      }
    });
  }, [apiKey, addRecentRepo, analysisState]);

  const handleGenerateDocs = useCallback(async () => {
    if (!repoUrl || !apiKey) return;
    try {
      const docs = await generateDocs(repoUrl, branchName || null, apiKey);
      setAnalysisData(prev => ({ ...prev, docs }));
      setActiveTab('docs');
    } catch (error) {
      setErrorMessage(error.message);
    }
  }, [repoUrl, branchName, apiKey]);

  const handleReset = useCallback(() => {
    setAnalysisState(ANALYSIS_STATES.IDLE);
    setAnalysisData({
      report: null,
      fileReviews: [],
      progress: { current: 0, total: 0, currentFile: '', phase: '' },
      issues: [],
      stats: null,
      docs: null,
    });
    setErrorMessage('');
    setActiveTab('review');
  }, []);

  const isIdle = analysisState === ANALYSIS_STATES.IDLE;
  const isAnalyzing = analysisState === ANALYSIS_STATES.CLONING || analysisState === ANALYSIS_STATES.ANALYZING;
  const isComplete = analysisState === ANALYSIS_STATES.COMPLETE;
  const isError = analysisState === ANALYSIS_STATES.ERROR;

  return (
    <div className="app">
      <Header apiKey={apiKey} />

      <main className="app-main">
        {isIdle && <HeroSection />}

        {(isIdle || isError) && (
          <RepoInput
            onAnalyze={handleAnalyze}
            isLoading={isAnalyzing}
            errorMessage={errorMessage}
            apiKey={apiKey}
            onApiKeyChange={setApiKey}
          />
        )}

        {isAnalyzing && (
          <AnalysisProgress
            progress={analysisData.progress}
            fileReviews={analysisData.fileReviews}
            issueCount={analysisData.issues.length}
          />
        )}

        {isComplete && (
          <>
            <section className="results-header container animate-fade-in">
              <div className="results-header-content">
                <div className="results-title-row">
                  <h2>
                    Analysis Complete
                    <span className="results-check">✓</span>
                  </h2>
                  <button className="btn btn-ghost" onClick={handleReset}>
                    ← New Analysis
                  </button>
                </div>
                <p className="results-repo">{repoUrl}</p>
              </div>
            </section>

            <nav className="tab-navigation container" role="tablist" aria-label="Results tabs">
              <button
                role="tab"
                aria-selected={activeTab === 'review'}
                className={`tab-btn ${activeTab === 'review' ? 'active' : ''}`}
                onClick={() => setActiveTab('review')}
              >
                <span className="tab-icon">🔍</span>
                Code Review
                {analysisData.issues.length > 0 && (
                  <span className="tab-count">{analysisData.issues.length}</span>
                )}
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'docs'}
                className={`tab-btn ${activeTab === 'docs' ? 'active' : ''}`}
                onClick={() => setActiveTab('docs')}
              >
                <span className="tab-icon">📝</span>
                Documentation
              </button>
              <button
                role="tab"
                aria-selected={activeTab === 'stats'}
                className={`tab-btn ${activeTab === 'stats' ? 'active' : ''}`}
                onClick={() => setActiveTab('stats')}
              >
                <span className="tab-icon">📊</span>
                Statistics
              </button>
              <div
                className="tab-indicator"
                style={{
                  transform: `translateX(${
                    activeTab === 'review' ? 0 :
                    activeTab === 'docs' ? 100 :
                    200
                  }%)`,
                }}
              />
            </nav>

            <section className="tab-content container">
              {activeTab === 'review' && (
                <ReviewPanel
                  fileReviews={analysisData.fileReviews}
                  issues={analysisData.issues}
                />
              )}
              {activeTab === 'docs' && (
                <DocsViewer
                  docs={analysisData.docs}
                  onGenerateDocs={handleGenerateDocs}
                  repoUrl={repoUrl}
                />
              )}
              {activeTab === 'stats' && (
                <StatsOverview
                  stats={analysisData.stats}
                  issues={analysisData.issues}
                  fileReviews={analysisData.fileReviews}
                />
              )}
            </section>
          </>
        )}

        {isError && !errorMessage && (
          <div className="error-banner container animate-shake">
            <span className="error-icon">⚠️</span>
            <p>Something went wrong. Please try again.</p>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
