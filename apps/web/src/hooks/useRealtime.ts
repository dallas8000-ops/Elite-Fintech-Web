import { useEffect, useRef, useState, useCallback } from "react";
import { getWsUrl, type PaymentEvent, type Subscription } from "../lib/api";

interface RealtimeState {
  connected: boolean;
  events: PaymentEvent[];
  subscription: Subscription | null;
  setSubscription: (sub: Subscription | null) => void;
  setInitialEvents: (events: PaymentEvent[]) => void;
}

export function useRealtime(token: string | null): RealtimeState {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [events, setEvents] = useState<PaymentEvent[]>([]);
  const [subscription, setSubscriptionState] = useState<Subscription | null>(null);

  const setSubscription = useCallback((sub: Subscription | null) => {
    setSubscriptionState(sub);
  }, []);

  const setInitialEvents = useCallback((initial: PaymentEvent[]) => {
    setEvents(initial);
  }, []);

  useEffect(() => {
    if (!token) return;

    const ws = new WebSocket(getWsUrl(token));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);

    ws.onmessage = (msg) => {
      try {
        const payload = JSON.parse(msg.data);
        if (payload.type === "connected") return;

        if (payload.event === "payment:event") {
          setEvents((prev) => [payload.data as PaymentEvent, ...prev].slice(0, 100));
        }
        if (payload.event === "subscription:updated") {
          setSubscriptionState(payload.data as Subscription);
        }
      } catch {
        /* ignore malformed */
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [token]);

  return { connected, events, subscription, setSubscription, setInitialEvents };
}
