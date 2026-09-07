import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**", "node_modules/**"] },
  eslint.configs.recommended,
  tseslint.configs.recommended,
  {
    rules: {
      // Gateway logs through pino; bare console is a smell. console.error
      // stays allowed for the boot-fatal path (pino isn't up yet).
      "no-console": ["error", { allow: ["error"] }],
    },
  },
);
