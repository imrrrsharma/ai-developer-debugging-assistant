import { useState } from "react";
import SeverityBadge from "./SeverityBadge";
import styles from "./AnalysisResult.module.css";

const LOG_TYPE_LABELS = {
  java_spring: "Java Spring Boot",
  java_generic: "Java",
  nodejs: "Node.js",
  python: "Python",
  generic: "Generic",
};

export default function AnalysisResult({ result }) {
  const [expandedFix, setExpandedFix] = useState(null);
  const [showRawLog, setShowRawLog] = useState(false);
  const [copiedIdx, setCopiedIdx] = useState(null);

  if (!result) return null;

  const {
    error_type,
    root_cause,
    explanation,
    fix_suggestions,
    severity,
    confidence,
    possible_causes,
    quick_fixes,
    highlighted_lines,
    log_type,
    error_message,
    service_name,
    processing_time_ms,
    model_used,
    raw_log,
  } = result;

  function copyCommand(cmd, idx) {
    navigator.clipboard.writeText(cmd);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 1500);
  }

  const confidencePct = Math.round((confidence || 0) * 100);

  return (
    <div className={styles.container}>
      {/* Header row */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h2 className={styles.errorType}>{error_type}</h2>
          <span className={styles.logTypeBadge}>
            {LOG_TYPE_LABELS[log_type] || log_type}
          </span>
          {service_name && (
            <span className={styles.serviceBadge}>{service_name}</span>
          )}
        </div>
        <div className={styles.headerRight}>
          <SeverityBadge severity={severity} />
          <div className={styles.confidenceWrap}>
            <span className={styles.confidenceLabel}>Confidence</span>
            <div className={styles.confidenceBar}>
              <div
                className={styles.confidenceFill}
                style={{
                  width: `${confidencePct}%`,
                  background: confidencePct > 75 ? "#16a34a" : confidencePct > 40 ? "#ca8a04" : "#dc2626",
                }}
              />
            </div>
            <span className={styles.confidencePct}>{confidencePct}%</span>
          </div>
        </div>
      </div>

      {/* Error message */}
      {error_message && (
        <div className={styles.errorMsg}>
          <span className={styles.sectionLabel}>Error Message</span>
          <code className={styles.errorCode}>{error_message}</code>
        </div>
      )}

      {/* Root cause */}
      <Section title="Root Cause" icon="🔍">
        <p className={styles.bodyText}>{root_cause}</p>
      </Section>

      {/* Explanation */}
      <Section title="Explanation" icon="📖">
        <p className={styles.bodyText}>{explanation}</p>
      </Section>

      {/* Possible causes */}
      {possible_causes?.length > 0 && (
        <Section title="Possible Causes" icon="⚠️">
          <ol className={styles.causeList}>
            {possible_causes.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ol>
        </Section>
      )}

      {/* Fix suggestions */}
      {fix_suggestions?.length > 0 && (
        <Section title="Fix Suggestions" icon="🛠️">
          <ul className={styles.fixList}>
            {fix_suggestions.map((fix, i) => (
              <li
                key={i}
                className={`${styles.fixItem} ${expandedFix === i ? styles.fixItemExpanded : ""}`}
                onClick={() => setExpandedFix(expandedFix === i ? null : i)}
              >
                <span className={styles.fixBullet}>{i + 1}</span>
                <span className={styles.fixText}>{fix}</span>
                <span className={styles.fixArrow}>{expandedFix === i ? "▲" : "▼"}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Quick fix buttons */}
      {quick_fixes?.length > 0 && (
        <Section title="Quick Fixes" icon="⚡">
          <div className={styles.quickFixGrid}>
            {quick_fixes.map((qf, i) => (
              <div key={i} className={styles.quickFixCard}>
                <div className={styles.quickFixHeader}>
                  <span className={styles.quickFixLabel}>{qf.label}</span>
                  {qf.command && (
                    <button
                      className={styles.copyBtn}
                      onClick={() => copyCommand(qf.command, i)}
                    >
                      {copiedIdx === i ? "✓ Copied" : "Copy"}
                    </button>
                  )}
                </div>
                <p className={styles.quickFixAction}>{qf.action}</p>
                {qf.command && (
                  <code className={styles.quickFixCmd}>{qf.command}</code>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Highlighted log lines */}
      {raw_log && highlighted_lines?.length > 0 && (
        <Section title="Highlighted Log Lines" icon="📋">
          <div className={styles.logViewer}>
            {raw_log.split("\n").map((line, i) => (
              <div
                key={i}
                className={`${styles.logLine} ${highlighted_lines.includes(i) ? styles.logLineError : ""}`}
              >
                <span className={styles.lineNum}>{i + 1}</span>
                <span className={styles.lineContent}>{line}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Footer meta */}
      <div className={styles.footer}>
        <span>Model: {model_used}</span>
        <span>Time: {processing_time_ms}ms</span>
        {raw_log && (
          <button
            className={styles.rawToggle}
            onClick={() => setShowRawLog((v) => !v)}
          >
            {showRawLog ? "Hide" : "Show"} Raw Log
          </button>
        )}
      </div>

      {showRawLog && raw_log && (
        <pre className={styles.rawLog}>{raw_log}</pre>
      )}
    </div>
  );
}

function Section({ title, icon, children }) {
  const [open, setOpen] = useState(true);
  return (
    <div className={styles.section}>
      <button className={styles.sectionToggle} onClick={() => setOpen((v) => !v)}>
        <span>{icon} {title}</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className={styles.sectionBody}>{children}</div>}
    </div>
  );
}
