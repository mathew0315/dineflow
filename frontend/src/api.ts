// 與後端 API 溝通的唯一入口：統一處理 token、錯誤訊息、401 登出

export type Role = "owner" | "staff";
export type Channel = "online" | "pos";
export type OrderStatus = "pending" | "preparing" | "ready" | "completed" | "cancelled";

export interface Store { id: number; name: string; slug: string; is_open: boolean }
export interface MenuItem { id: number; name: string; category: string; price: number; is_available: boolean }
export interface OrderItem { menu_item_id: number; name: string; unit_price: number; quantity: number; subtotal: number }
export interface Order {
  id: number; channel: Channel; status: OrderStatus;
  payment_method: "cash" | "linepay"; payment_status: "unpaid" | "paid" | "refunded";
  customer_name: string | null; table_no: string | null; note: string | null;
  total: number; created_at: string; items: OrderItem[];
}
export interface Me { id: number; email: string; role: Role }
export interface DailyReport {
  date: string; order_count: number; revenue: number;
  by_channel: Record<string, number>; top_items: { name: string; quantity: number }[];
}

const TOKEN_KEY = "dineflow_token";

export const auth = {
  get: (): string | null => { try { return localStorage.getItem(TOKEN_KEY); } catch { return null; } },
  set: (t: string) => { try { localStorage.setItem(TOKEN_KEY, t); } catch { /* 私密模式等情況 */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY); } catch { /* ignore */ } },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

function detailToMessage(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    // FastAPI 422：取第一個欄位錯誤，轉成看得懂的說明
    const d = detail[0] as { loc?: unknown[]; msg?: string };
    const field = String(d.loc?.[d.loc.length - 1] ?? "");
    const names: Record<string, string> = {
      customer_phone: "手機號碼", customer_name: "姓名", email: "Email", password: "密碼",
      slug: "店家代號", price: "價格", name: "名稱", items: "品項",
    };
    return `${names[field] ?? field} 格式不正確`;
  }
  return "發生錯誤，請稍後再試";
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = auth.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers, body });
  } catch {
    throw new ApiError(0, "連不上伺服器。免費主機休眠中時，第一次開啟約需 1 分鐘，請稍候再試");
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401 && path !== "/api/auth/login") {
      auth.clear();
      if (!location.pathname.startsWith("/login")) location.assign("/login?expired=1");
    }
    throw new ApiError(res.status, detailToMessage((data as { detail?: unknown }).detail));
  }
  return data as T;
}

export const nt = (n: number) => `NT$${n.toLocaleString("zh-TW")}`;

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "已收單", preparing: "製作中", ready: "可取餐", completed: "已完成", cancelled: "已取消",
};

export function timeOf(iso: string) {
  return new Date(iso).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function minutesAgo(iso: string) {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  return m === 0 ? "剛剛" : `${m} 分鐘前`;
}
