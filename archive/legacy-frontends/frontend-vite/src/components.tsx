import { useEffect, useRef, type ReactNode } from "react";
import { labels } from "./types";
export type IconName =
  | "cross"
  | "cases"
  | "tasks"
  | "dashboard"
  | "dispatch"
  | "chat"
  | "logout"
  | "user"
  | "bot"
  | "sparkles"
  | "chevron";

export function Icon({ name }: { name: IconName }) {
  return (
    <svg
      aria-hidden="true"
      className="icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {name === "cross" && <><path d="M12 4v16M4 12h16" strokeWidth="2.8" /></>}
      {name === "cases" && (
        <>
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="M8 8h8M8 12h8M8 16h5" />
        </>
      )}
      {name === "tasks" && (
        <>
          <rect x="4" y="3" width="16" height="18" rx="2" />
          <path d="m8 9 1.5 1.5L12 8M14 9h3m-9 7 1.5 1.5L12 15m2 1h3" />
        </>
      )}
      {name === "dashboard" && (
        <>
          <rect x="3" y="3" width="7" height="9" rx="1" />
          <rect x="14" y="3" width="7" height="5" rx="1" />
          <rect x="14" y="12" width="7" height="9" rx="1" />
          <rect x="3" y="16" width="7" height="5" rx="1" />
        </>
      )}
      {name === "dispatch" && (
        <>
          <circle cx="6" cy="6" r="3" />
          <circle cx="6" cy="18" r="3" />
          <line x1="20" y1="4" x2="8.5" y2="4" />
          <polyline points="10 9 17 9 20 12 20 18 16 18" />
          <circle cx="16" cy="18" r="2" />
          <circle cx="9" cy="18" r="2" />
        </>
      )}
      {name === "chat" && (
        <>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </>
      )}
      {name === "logout" && (
        <>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </>
      )}
      {name === "user" && (
        <>
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </>
      )}
      {name === "bot" && (
        <>
          <rect x="3" y="11" width="18" height="10" rx="2" />
          <circle cx="12" cy="5" r="2" />
          <path d="M12 7v4" />
          <line x1="8" y1="16" x2="8.01" y2="16" strokeWidth="2.5" />
          <line x1="16" y1="16" x2="16.01" y2="16" strokeWidth="2.5" />
        </>
      )}
      {name === "sparkles" && (
        <>
          <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z" />
        </>
      )}
      {name === "chevron" && (
        <>
          <polyline points="6 9 12 15 18 9" />
        </>
      )}
    </svg>
  );
}
export function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{labels[value] ?? value}</span>;
}
export function Modal({
  title,
  children,
  onClose,
  variant,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  variant?: "drawer";
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const previous = useRef(document.activeElement as HTMLElement);
  useEffect(() => {
    const node = dialog.current!;
    node.showModal();
    return () => {
      node.close();
      queueMicrotask(() => {
        if (previous.current?.isConnected) previous.current.focus();
      });
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      className={variant === "drawer" ? "drawer-dialog" : undefined}
      aria-labelledby="dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header className="modal-head">
        <h2 id="dialog-title">{title}</h2>
        <button onClick={onClose} aria-label="Đóng panel">
          ✕
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function ErrorBox({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error" role="alert">
      {message}
      {retry && <button onClick={retry}>Thử lại</button>}
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
