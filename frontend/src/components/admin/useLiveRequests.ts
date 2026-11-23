import { useCallback, useEffect, useState } from "react";
import { fetchLiveRequests, type LiveRequest } from "../../services/api";

/** Polls the waiting "talk to a counsellor" requests. Shared by the banner and the tab. */
export function useLiveRequests(adminKey: string, everyMs = 4000) {
  const [requests, setRequests] = useState<LiveRequest[]>([]);
  const [inHours, setInHours] = useState<boolean | null>(null);
  const load = useCallback(async () => {
    if (!adminKey) return;
    try {
      const r = await fetchLiveRequests(adminKey);
      setRequests(r.requests);
      setInHours(r.in_office_hours);
    } catch {
      /* keep the last list; try again on the next tick */
    }
  }, [adminKey]);
  useEffect(() => {
    const first = window.setTimeout(load, 0);
    const id = window.setInterval(load, everyMs);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(id);
    };
  }, [load, everyMs]);
  return { requests, inHours, reload: load };
}

