import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaptureFeed } from "./capture-feed";

describe("CaptureFeed", () => {
  it("shows source, text, and processing state", () => {
    render(
      <CaptureFeed
        items={[
          {
            id: "018f0000-0000-7000-8000-000000000001",
            receivedAt: "2026-07-14T12:00:00Z",
            originalText: "第一条 Spark",
            normalizedText: "第一条 Spark",
            processingState: "processed",
            source: "telegram",
          },
        ]}
      />,
    );

    expect(screen.getByText("第一条 Spark")).toBeInTheDocument();
    expect(screen.getByText("已处理")).toBeInTheDocument();
    expect(screen.getByText("Telegram")).toBeInTheDocument();
  });

  it("shows a capture-specific empty state", () => {
    render(<CaptureFeed items={[]} />);

    expect(screen.getByText("还没有 Spark")).toBeInTheDocument();
    expect(screen.getByText(/Telegram Bot/)).toBeInTheDocument();
  });
});
