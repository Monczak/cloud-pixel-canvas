export function getApiBase(): string {
  return "/api";
}

export function getWebSocketBase(): string {
  return getApiBase() + "/ws";
}

let isRefreshing = false;
let refreshSubscribers: ((success: boolean) => void)[] = [];

function subscribeToRefresh(cb: (success: boolean) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(success: boolean) {
  refreshSubscribers.forEach((cb) => cb(success));
  refreshSubscribers = [];
}

export async function fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const res = await fetch(input, init);

  if (res.status === 401) {
    if (isRefreshing) {
      // Already refreshing, wait for it
      return new Promise((resolve) => {
        subscribeToRefresh(async (success) => {
          if (success) {
            resolve(await fetch(input, init));
          } else {
            resolve(res); // Return original 401
          }
        });
      });
    }

    isRefreshing = true;

    try {
      const email = typeof localStorage !== "undefined" ? localStorage.getItem("user_email") : "";

      // Attempt refresh
      const refreshRes = await fetch(`${getApiBase()}/auth/refresh`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email})
      });

      if (refreshRes.ok) {
        onRefreshed(true);
        isRefreshing = false;
        // Retry original request
        return await fetch(input, init);
      } else {
        onRefreshed(false);
        isRefreshing = false;
        return res;
      }
    } catch (err) {
      onRefreshed(false);
      isRefreshing = false;
      return res;
    }
  }

  return res;
}