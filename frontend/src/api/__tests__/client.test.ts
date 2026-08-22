import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

describe("API base URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("uses same-origin API paths when no override is configured", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "");
    vi.stubEnv("VITE_API_BASE_URL", "");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("");
  });

  it("uses the configured API URL for separate development servers", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "http://localhost:8000");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("removes trailing slashes from the configured API URL", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "http://localhost:8000///");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("supports the legacy API URL environment variable", async () => {
    vi.stubEnv("VITE_AUTHSTATUS_API_BASE_URL", "");
    vi.stubEnv("VITE_API_BASE_URL", "http://127.0.0.1:8000/");

    const { API_BASE_URL } = await import("../client");

    expect(API_BASE_URL).toBe("http://127.0.0.1:8000");
  });
});


class FakeBroadcastChannel {
  static instances: FakeBroadcastChannel[] = [];

  readonly name: string;
  readonly postMessage = vi.fn();
  private messageListener:
    | ((event: MessageEvent<unknown>) => void)
    | null = null;

  constructor(name: string) {
    this.name = name;
    FakeBroadcastChannel.instances.push(this);
  }

  addEventListener(
    type: string,
    listener: (event: MessageEvent<unknown>) => void
  ) {
    if (type === "message") {
      this.messageListener = listener;
    }
  }

  emitMessage(data: unknown) {
    this.messageListener?.(
      new MessageEvent("message", {
        data,
      })
    );
  }
}

describe("authenticatedFetch session expiration", () => {
  beforeEach(() => {
    FakeBroadcastChannel.instances = [];
  
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal(
      "BroadcastChannel",
      FakeBroadcastChannel
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("reports the updated session expiration from authenticated responses", async () => {
    const expiresAt = "2026-08-22T10:30:00+00:00";

    vi.mocked(fetch).mockResolvedValue(
      new Response(null, {
        status: 200,
        headers: {
          "X-CareQueue-Session-Expires-At": expiresAt,
        },
      })
    );

    const {
      authenticatedFetch,
      subscribeToSessionExpiration,
    } = await import("../client");

    const listener = vi.fn();
    const unsubscribe = subscribeToSessionExpiration(listener);

    await authenticatedFetch("/api/test");

    expect(listener).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledWith(expiresAt);

    unsubscribe();
  });

  it("does not report a session expiration when the header is absent", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(null, {
        status: 200,
      })
    );

    const {
      authenticatedFetch,
      subscribeToSessionExpiration,
    } = await import("../client");

    const listener = vi.fn();
    const unsubscribe = subscribeToSessionExpiration(listener);

    await authenticatedFetch("/api/test");

    expect(listener).not.toHaveBeenCalled();

    unsubscribe();
  });

  it("broadcasts updated session expiration to other tabs", async () => {
    const expiresAt = "2026-08-22T10:30:00+00:00";
  
    vi.mocked(fetch).mockResolvedValue(
      new Response(null, {
        status: 200,
        headers: {
          "X-CareQueue-Session-Expires-At": expiresAt,
        },
      })
    );
  
    const { authenticatedFetch } = await import("../client");
  
    await authenticatedFetch("/api/test");
  
    expect(FakeBroadcastChannel.instances).toHaveLength(2);

    const channel = FakeBroadcastChannel.instances.find(
      (candidate) =>
        candidate.name === "carequeue-session-expiration"
    );
    
    expect(channel).toBeDefined();
    
    if (!channel) {
      throw new Error(
        "Session expiration BroadcastChannel was not created."
      );
    }
    
    expect(channel.postMessage).toHaveBeenCalledOnce();
    expect(channel.postMessage).toHaveBeenCalledWith(
      expiresAt
    );
  });

  it("reports session expiration received from another tab", async () => {
    const expiresAt = "2026-08-22T10:45:00+00:00";
  
    const { subscribeToSessionExpiration } = await import(
      "../client"
    );
  
    const listener = vi.fn();
    const unsubscribe =
      subscribeToSessionExpiration(listener);
  
    expect(FakeBroadcastChannel.instances).toHaveLength(2);
  
    const expirationChannel = FakeBroadcastChannel.instances.find(
      (channel) =>
        channel.name === "carequeue-session-expiration"
    );
  
    expect(expirationChannel).toBeDefined();
  
    if (!expirationChannel) {
      throw new Error(
        "Session expiration BroadcastChannel was not created."
      );
    }
  
    expirationChannel.emitMessage(expiresAt);
  
    expect(listener).toHaveBeenCalledOnce();
    expect(listener).toHaveBeenCalledWith(expiresAt);
  
    unsubscribe();
  });

  it("ignores non-string messages from the session channel", async () => {
    const { subscribeToSessionExpiration } = await import(
      "../client"
    );
  
    const listener = vi.fn();
    const unsubscribe =
      subscribeToSessionExpiration(listener);
  
    const expirationChannel = FakeBroadcastChannel.instances.find(
      (channel) =>
        channel.name === "carequeue-session-expiration"
    );
  
    expect(expirationChannel).toBeDefined();
  
    if (!expirationChannel) {
      throw new Error(
        "Session expiration BroadcastChannel was not created."
      );
    }
  
    expirationChannel.emitMessage({
      expires_at: "invalid-message-shape",
    });
  
    expect(listener).not.toHaveBeenCalled();
  
    unsubscribe();
  });

  it("broadcasts session logout to other tabs", async () => {
    const { broadcastSessionLogout } = await import("../client");
  
    expect(FakeBroadcastChannel.instances).toHaveLength(2);
  
    const logoutChannel = FakeBroadcastChannel.instances.find(
      (channel) => channel.name === "carequeue-session-logout"
    );
    
    expect(logoutChannel).toBeDefined();
    
    if (!logoutChannel) {
      throw new Error(
        "Session logout BroadcastChannel was not created."
      );
    }
    
    broadcastSessionLogout();
    
    expect(logoutChannel.postMessage).toHaveBeenCalledOnce();
    expect(logoutChannel.postMessage).toHaveBeenCalledWith(
      "logout"
    );
  });

  it("reports session logout received from another tab", async () => {
    const { subscribeToSessionLogout } = await import("../client");
  
    const listener = vi.fn();
    const unsubscribe = subscribeToSessionLogout(listener);
  
    const logoutChannel = FakeBroadcastChannel.instances.find(
      (channel) => channel.name === "carequeue-session-logout"
    );
  
    expect(logoutChannel).toBeDefined();
  
    if (!logoutChannel) {
      throw new Error(
        "Session logout BroadcastChannel was not created."
      );
    }
  
    logoutChannel.emitMessage("logout");
  
    expect(listener).toHaveBeenCalledOnce();
  
    unsubscribe();
  });

  it("ignores invalid messages on the session logout channel", async () => {
    const { subscribeToSessionLogout } = await import("../client");
  
    const listener = vi.fn();
    const unsubscribe = subscribeToSessionLogout(listener);
  
    const logoutChannel = FakeBroadcastChannel.instances.find(
      (channel) => channel.name === "carequeue-session-logout"
    );
  
    expect(logoutChannel).toBeDefined();
  
    if (!logoutChannel) {
      throw new Error(
        "Session logout BroadcastChannel was not created."
      );
    }
  
    logoutChannel.emitMessage("not-logout");
    logoutChannel.emitMessage({
      type: "logout",
    });
  
    expect(listener).not.toHaveBeenCalled();
  
    unsubscribe();
  });
});