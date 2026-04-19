import { useState, useCallback } from "react";
import { api } from "./api/client";
import LogInput from "./components/LogInput";
import AnalysisResult from "./components/AnalysisResult";
import HistoryPanel from "./components/HistoryPanel";
import styles from "./App.module.css";

export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [theme, setTheme] = useState("light");
  const [historyKey, setHistoryKey] = useState(0);

  const handleAnalyze = useCallback(async ({ type, content, file, hint }) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setActiveSessionId(null);
    try {
      const data = type === "file"
        ? await api.analyzeFile(file, hint)
        : await api.analyzeText(content, hint);
      setResult(data);
      setActiveSessionId(data.session_id);
      setHistoryKey((k) => k + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSelectSession = useCallback(async (sessionId) => {
    if (sessionId === activeSessionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getSessionDetail(sessionId);
      setResult(data);
      setActiveSessionId(sessionId);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [activeSessionId]);

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  return (
    <div className={styles.root} data-theme={theme}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.logo}>🐛</span>
          <div>
            <h1 className={styles.title}>AI Debugging Assistant</h1>
            <p className={styles.subtitle}>Powered by GPT-4 · Root cause analysis for enterprise logs</p>
          </div>
        </div>
        <button className={styles.themeBtn} onClick={toggleTheme} title="Toggle theme">
          {theme === "light" ? "🌙" : "☀️"}
        </button>
      </header>

      <main className={styles.main}>
        <div className={styles.leftCol}>
          <LogInput onAnalyze={handleAnalyze} loading={loading} />
          {error && <div className={styles.errorBanner}>Error: {error}</div>}
          {loading && !result && <LoadingSkeleton />}
          {result && <AnalysisResult result={result} />}
        </div>

        <div className={styles.rightCol}>
          <HistoryPanel
            key={historyKey}
            onSelectSession={handleSelectSession}
            activeSessionId={activeSessionId}
          />
        </div>
      </main>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className={styles.skeleton}>
      {[200, 140, 180, 100].map((w, i) => (
        <div key={i} className={styles.skeletonLine} style={{ width: `${w}px` }} />
      ))}
    </div>
  );
}
