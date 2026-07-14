import { z } from "zod";

const apiBase = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const currentUserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  timezone: z.string(),
});

const captureItemSchema = z
  .object({
    id: z.string().uuid(),
    received_at: z.iso.datetime(),
    original_text: z.string().nullable(),
    normalized_text: z.string().nullable(),
    processing_state: z.enum([
      "queued",
      "processing",
      "processed",
      "needs_attention",
      "failed",
    ]),
    source: z.literal("telegram"),
  })
  .transform((item) => ({
    id: item.id,
    receivedAt: item.received_at,
    originalText: item.original_text,
    normalizedText: item.normalized_text,
    processingState: item.processing_state,
    source: item.source,
  }));

const captureFeedSchema = z.object({
  items: z.array(captureItemSchema),
  next_cursor: z.string().nullable(),
});

export type CurrentUser = z.infer<typeof currentUserSchema>;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function serverRequest(path: string, cookieHeader: string): Promise<Response> {
  return fetch(`${apiBase}${path}`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });
}

export async function getCurrentUser(cookieHeader: string): Promise<CurrentUser | null> {
  const response = await serverRequest("/api/auth/me", cookieHeader);
  if (response.status === 401) return null;
  if (!response.ok) throw new ApiError("无法验证当前登录状态", response.status);
  return currentUserSchema.parse(await response.json());
}

export async function getCaptures(cookieHeader: string) {
  const response = await serverRequest("/api/captures?limit=50", cookieHeader);
  if (!response.ok) throw new ApiError("暂时无法读取 Spark", response.status);
  const result = captureFeedSchema.parse(await response.json());
  return { items: result.items, nextCursor: result.next_cursor };
}
