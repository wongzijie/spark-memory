import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";

import { CaptureFeed } from "@/components/capture-feed";
import { LogoutButton } from "@/components/logout-button";
import { getCaptures, getCurrentUser } from "@/lib/api";

function serializeCookies(values: { name: string; value: string }[]) {
  return values.map(({ name, value }) => `${name}=${value}`).join("; ");
}

export default async function DashboardPage() {
  const cookieStore = await cookies();
  const cookieHeader = serializeCookies(cookieStore.getAll());
  const user = await getCurrentUser(cookieHeader);
  if (!user) redirect("/login");
  const { items } = await getCaptures(cookieHeader);

  return (
    <main className="dashboard-shell">
      <header className="dashboard-header">
        <Link className="wordmark" href="/" aria-label="刷新 Spark Memory">
          SPARK—MEMORY
        </Link>
        <div className="header-actions">
          <a className="settings-link" href="#settings" aria-label="设置即将开放">
            设置 / Settings <span>SOON</span>
          </a>
          <LogoutButton />
        </div>
      </header>

      <aside className="dashboard-rail" aria-label="当前记忆本信息">
        <p className="eyebrow">MEMORY BOOK / 记忆本</p>
        <h1>你的<br />Spark 流</h1>
        <p className="rail-copy">
          不用分类，不用打断思路。所有输入先落在这里，再由 Agent 慢慢理解。
        </p>
        <dl className="rail-stats">
          <div><dt>当前显示</dt><dd>{items.length}</dd></div>
          <div><dt>入口</dt><dd>Telegram</dd></div>
          <div><dt>账户</dt><dd>{user.email}</dd></div>
        </dl>
      </aside>

      <section className="feed-panel">
        <div className="feed-heading">
          <div>
            <p className="section-index">LATEST / 最新</p>
            <h2>刚刚捕捉的念头</h2>
          </div>
          <p>按时间倒序 · Newest first</p>
        </div>
        <CaptureFeed items={items} />
      </section>

      <aside className="future-panel" id="settings">
        <p className="section-index">NEXT / 接下来</p>
        <h2>Agent 正在成长</h2>
        <p>
          分类规则、智能跟进、联网更新与个人 API Key 管理会在后续里程碑逐步来到这里。
        </p>
        <ul>
          <li><span>01</span> 自动勾稽与知识图谱</li>
          <li><span>02</span> Tavily 联网 Follow-up</li>
          <li><span>03</span> 语音、手写与视频</li>
        </ul>
      </aside>
    </main>
  );
}
