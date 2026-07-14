import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import Link from "next/link";

import { LoginForm } from "@/components/login-form";
import { getCurrentUser } from "@/lib/api";

function serializeCookies(values: { name: string; value: string }[]) {
  return values.map(({ name, value }) => `${name}=${value}`).join("; ");
}

export default async function LoginPage() {
  const cookieStore = await cookies();
  const user = await getCurrentUser(serializeCookies(cookieStore.getAll()));
  if (user) redirect("/");

  return (
    <main className="login-shell">
      <section className="login-intro">
        <Link className="wordmark" href="/" aria-label="Spark Memory 首页">
          SPARK—MEMORY
        </Link>
        <div>
          <p className="eyebrow">THINK FIRST, ORGANIZE LATER</p>
          <h1>让念头<br />先发生。</h1>
          <p className="login-copy">
            先捕捉，再理解。Spark Memory 会把散乱、跨领域的想法留住，整理工作交给 Agent。
          </p>
          <p className="english-copy">
            Capture first. Let the agent connect, revisit, and organize what follows.
          </p>
        </div>
        <p className="edition-label">MVP · TELEGRAM CAPTURE</p>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <p className="section-index">01 / ACCESS</p>
          <h2>欢迎回来<br /><span>Welcome back</span></h2>
          <LoginForm />
          <p className="login-footnote">
            当前为单用户 MVP。注册与个人 Key 管理将在后续版本开放。
          </p>
        </div>
      </section>
    </main>
  );
}
