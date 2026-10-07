"use client";

import * as React from "react";

/**
 * Holds one key for one user intent. Network retries deliberately reuse it; a changed
 * payload or confirmed success starts a new intent.
 */
export function useIntentKey(fingerprint: string) {
  const fingerprintRef = React.useRef(fingerprint);
  const keyRef = React.useRef(crypto.randomUUID());
  const [, render] = React.useReducer((count) => count + 1, 0);
  if (fingerprintRef.current !== fingerprint) {
    fingerprintRef.current = fingerprint;
    keyRef.current = crypto.randomUUID();
  }
  const reset = React.useCallback(() => { keyRef.current = crypto.randomUUID(); render(); }, []);
  return { key: keyRef.current, reset };
}
