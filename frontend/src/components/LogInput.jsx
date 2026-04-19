import { useState, useRef } from "react";
import styles from "./LogInput.module.css";

export default function LogInput({ onAnalyze, loading }) {
  const [text, setText] = useState("");
  const [hint, setHint] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState(null);
  const [fileObj, setFileObj] = useState(null);
  const fileRef = useRef();

  function handleFile(file) {
    if (!file) return;
    setFileName(file.name);
    setFileObj(file);
    setText("");
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (fileObj) {
      onAnalyze({ type: "file", file: fileObj, hint });
    } else if (text.trim()) {
      onAnalyze({ type: "text", content: text.trim(), hint });
    }
  }

  function handleClear() {
    setText("");
    setFileName(null);
    setFileObj(null);
    setHint("");
  }

  return (
    <form className={styles.container} onSubmit={handleSubmit}>
      <h2 className={styles.heading}>Paste Logs or Upload a File</h2>

      <div
        className={`${styles.dropzone} ${dragOver ? styles.dragOver : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !fileObj && fileRef.current.click()}
      >
        {fileName ? (
          <span className={styles.fileName}>📄 {fileName}</span>
        ) : (
          <span className={styles.dropHint}>
            Drag &amp; drop a log file here, or{" "}
            <span className={styles.link}>browse</span>
          </span>
        )}
        <input
          ref={fileRef}
          type="file"
          accept=".log,.txt,.out,.json"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files[0])}
        />
      </div>

      <div className={styles.divider}><span>or paste logs below</span></div>

      <textarea
        className={styles.textarea}
        value={text}
        onChange={(e) => { setText(e.target.value); setFileName(null); setFileObj(null); }}
        placeholder={"2024-03-15 14:23:01.542 ERROR org.springframework.boot.SpringApplication - Application run failed\njava.lang.NullPointerException: Cannot invoke method get() on null object\n\tat com.example.service.UserService.findUser(UserService.java:42)"}
        rows={14}
        spellCheck={false}
        disabled={!!fileName}
      />

      <input
        className={styles.hintInput}
        type="text"
        value={hint}
        onChange={(e) => setHint(e.target.value)}
        placeholder="Optional hint (e.g. Spring Boot 3.x, Node.js 18, Kafka 3.4)"
      />

      <div className={styles.actions}>
        <button
          type="button"
          className={styles.clearBtn}
          onClick={handleClear}
          disabled={loading}
        >
          Clear
        </button>
        <button
          type="submit"
          className={styles.analyzeBtn}
          disabled={loading || (!text.trim() && !fileObj)}
        >
          {loading ? (
            <><span className={styles.spinner} /> Analyzing…</>
          ) : (
            "Analyze Logs"
          )}
        </button>
      </div>
    </form>
  );
}
