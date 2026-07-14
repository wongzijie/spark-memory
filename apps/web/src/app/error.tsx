"use client";

export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main className="error-shell">
      <p className="eyebrow">CONNECTION INTERRUPTED</p>
      <h1>记忆没有丢，<br />只是暂时没连上。</h1>
      <p>请稍后再试。你的 Telegram 原始输入仍会被安全保留。</p>
      <button type="button" onClick={reset}>重新读取 / Try again</button>
    </main>
  );
}
