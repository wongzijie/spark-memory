export type CaptureItem = {
  id: string;
  receivedAt: string;
  originalText: string | null;
  normalizedText: string | null;
  processingState:
    | "queued"
    | "processing"
    | "processed"
    | "needs_attention"
    | "failed";
  source: "telegram";
};

const stateLabels: Record<CaptureItem["processingState"], string> = {
  queued: "等待处理",
  processing: "处理中",
  processed: "已处理",
  needs_attention: "需要关注",
  failed: "处理失败",
};

function formatReceivedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function CaptureFeed({ items }: { items: CaptureItem[] }) {
  if (items.length === 0) {
    return (
      <section className="empty-state" aria-labelledby="empty-title">
        <div className="empty-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <p className="eyebrow">CAPTURE / 捕捉</p>
        <h2 id="empty-title">还没有 Spark</h2>
        <p>
          把一闪而过的念头发给 Telegram Bot。你的第一条记忆会安静地出现在这里。
        </p>
      </section>
    );
  }

  return (
    <ol className="capture-feed" aria-label="记忆流">
      {items.map((item, index) => {
        const displayText =
          item.normalizedText ?? item.originalText ?? "（这条 Spark 暂无可显示的文字）";
        const wasNormalized =
          item.normalizedText !== null && item.normalizedText !== item.originalText;

        return (
          <li
            className="capture-card"
            key={item.id}
            style={{ "--feed-index": index } as React.CSSProperties}
          >
            <div className="capture-meta">
              <span className="source-label">Telegram</span>
              <time dateTime={item.receivedAt}>{formatReceivedAt(item.receivedAt)}</time>
            </div>
            <p className="capture-text">{displayText}</p>
            {wasNormalized ? (
              <details className="original-capture">
                <summary>查看原文 / Original</summary>
                <p>{item.originalText}</p>
              </details>
            ) : null}
            <div className={`state-pill state-${item.processingState}`}>
              <span aria-hidden="true" />
              {stateLabels[item.processingState]}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
