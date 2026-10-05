import js from "@eslint/js";
import ts from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
import next from "@next/eslint-plugin-next";

export default ts.config(
  { ignores: [".next/**", "node_modules/**", "generated/**", "next-env.d.ts", "test-results/**", "playwright-report/**"] },
  js.configs.recommended,
  ...ts.configs.recommended,
  { plugins: { "@next/next": next }, rules: next.configs.recommended.rules },
  { files: ["**/*.{ts,tsx}"], plugins: { "react-hooks": hooks }, rules: {
    "react-hooks/rules-of-hooks": "error", "react-hooks/exhaustive-deps": "warn",
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
  } },
  { files: ["**/*.mjs"], languageOptions: { globals: { process: "readonly" } } },
);
