import {
  Activity,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Bot,
  Calendar,
  Check,
  ChevronDown,
  CircleAlert,
  CircleCheck,
  CircleDot,
  ClipboardList,
  Clock,
  Copy,
  Cross,
  Database,
  Ellipsis,
  FileText,
  Filter,
  FlaskConical,
  Gauge,
  Inbox,
  Info,
  LayoutDashboard,
  Layers,
  ListChecks,
  LoaderCircle,
  LogOut,
  MessageSquare,
  Moon,
  Package,
  Pencil,
  Pill,
  Plus,
  RefreshCw,
  Route,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Sun,
  Trash2,
  TriangleAlert,
  User,
  X,
  type LucideIcon,
} from "lucide-react";

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
  | "chevron"
  | "search"
  | "plus"
  | "refresh"
  | "moon"
  | "sun"
  | "bell"
  | "shield"
  | "pill"
  | "alert"
  | "info"
  | "check"
  | "checkCircle"
  | "clock"
  | "doc"
  | "external"
  | "arrowLeft"
  | "arrowRight"
  | "package"
  | "list"
  | "layers"
  | "activity"
  | "inbox"
  | "filter"
  | "copy"
  | "edit"
  | "trash"
  | "send"
  | "more"
  | "database"
  | "flask"
  | "stethoscope"
  | "gauge"
  | "spinner"
  | "calendar"
  | "close"
  | "dot";

export const iconMap: Record<IconName, LucideIcon> = {
  cross: Cross,
  cases: ClipboardList,
  tasks: ListChecks,
  dashboard: LayoutDashboard,
  dispatch: Route,
  chat: MessageSquare,
  logout: LogOut,
  user: User,
  bot: Bot,
  sparkles: Sparkles,
  chevron: ChevronDown,
  search: Search,
  plus: Plus,
  refresh: RefreshCw,
  moon: Moon,
  sun: Sun,
  bell: Bell,
  shield: ShieldCheck,
  pill: Pill,
  alert: TriangleAlert,
  info: Info,
  check: Check,
  checkCircle: CircleCheck,
  clock: Clock,
  doc: FileText,
  external: ArrowUpRight,
  arrowLeft: ArrowLeft,
  arrowRight: ArrowRight,
  package: Package,
  list: ClipboardList,
  layers: Layers,
  activity: Activity,
  inbox: Inbox,
  filter: Filter,
  copy: Copy,
  edit: Pencil,
  trash: Trash2,
  send: Send,
  more: Ellipsis,
  database: Database,
  flask: FlaskConical,
  stethoscope: Stethoscope,
  gauge: Gauge,
  spinner: LoaderCircle,
  calendar: Calendar,
  close: X,
  dot: CircleDot,
};

export const alertGlyph = CircleAlert;

export function Icon({
  name,
  className = "size-4",
  strokeWidth = 1.8,
}: {
  name: IconName;
  className?: string;
  strokeWidth?: number;
}) {
  const Glyph = iconMap[name];
  return <Glyph aria-hidden="true" className={className} strokeWidth={strokeWidth} />;
}
