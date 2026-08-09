import { Suspense } from "react";
import { LoginForm } from "@/features/auth";

export default function LoginPage() {
  // LoginForm reads the `next` search param, so it must render inside Suspense.
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
