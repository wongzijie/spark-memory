export default function Loading() {
  return (
    <main className="loading-shell" aria-busy="true" aria-label="正在读取记忆">
      <p className="wordmark">SPARK—MEMORY</p>
      <div className="loading-grid">
        <div className="skeleton skeleton-title" />
        <div className="skeleton-stack">
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
        </div>
      </div>
      <span className="sr-only">正在读取你的 Spark…</span>
    </main>
  );
}
