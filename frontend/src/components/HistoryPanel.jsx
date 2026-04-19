import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import SeverityBadge from "./SeverityBadge";
import styles from "./HistoryPanel.module.css";

export default function HistoryPanel({ onSelectSession, activeSessionId }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const PAGE_SIZE = 20;

  const load = useCallback(async (p) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHistory(p, PAGE_SIZE);
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(1); }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  function formatDate(iso) {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function truncate(str, n = 60) {
    if (!str) return "—";
    return str.length > n ? str.slice(0, n) + "…" : str;
  }

  return (
    <aside className={styles.panel}>
      <div className={styles.panelHeader}>
        <h3 className={styles.panelTitle}>History</h3>
        <button className={styles.refreshBtn} onClick={() => load(1)} disabled={loading}>
          {loading ? "…" : "↻"}
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {items.length === 0 && !loading && (
        <div className={styles.empty}>No history yet. Analyze some logs!</div>
      )}

      <ul className={styles.list}>
        {items.map((item) => (
          <li
            key={item.session_id}
            className={`${styles.item} ${activeSessionId === item.session_id ? styles.itemActive : ""}`}
            onClick={() => onSelectSession(item.session_id)}
          >
            <div className={styles.itemTop}>
              <span className={styles.errorType}>{item.error_type || "Unknown"}</span>
              <SeverityBadge severity={item.severity} />
            </div>
            <div className={styles.itemMid}>
              {truncate(item.root_cause || item.error_message)}
            </div>
            <div className={styles.itemBot}>
              <span className={styles.logType}>{item.log_type || "generic"}</span>
              <span className={styles.date}>{formatDate(item.created_at)}</span>
            </div>
          </li>
        ))}
      </ul>

      {totalPages > 1 && (
        <div className={styles.pagination}>
          <button
            disabled={page === 1 || loading}
            onClick={() => load(page - 1)}
          >
            ‹ Prev
          </button>
          <span>{page} / {totalPages}</span>
          <button
            disabled={page === totalPages || loading}
            onClick={() => load(page + 1)}
          >
            Next ›
          </button>
        </div>
      )}
    </aside>
  );
}
