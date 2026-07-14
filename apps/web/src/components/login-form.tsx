"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const form = new FormData(event.currentTarget);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      });
      if (!response.ok) {
        setError(
          response.status === 401
            ? "邮箱或密码不正确 / Invalid email or password"
            : "暂时无法登录，请稍后重试 / Sign-in is temporarily unavailable",
        );
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("无法连接服务，请检查网络 / Unable to reach the service");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <label htmlFor="email">
        邮箱 <span>Email</span>
      </label>
      <input
        id="email"
        name="email"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        required
      />
      <label htmlFor="password">
        密码 <span>Password</span>
      </label>
      <input
        id="password"
        name="password"
        type="password"
        autoComplete="current-password"
        placeholder="••••••••••••"
        required
      />
      <p className="form-error" role="alert" aria-live="polite">
        {error}
      </p>
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "正在进入… / Signing in…" : "进入记忆本 / Sign in"}
      </button>
    </form>
  );
}
