// ─────────────────────────────────────────────
//  usePredictions – fetch risk predictions
// ─────────────────────────────────────────────
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Prediction, PaginatedResponse } from "@/types";

interface Filters {
  course_id?: number;
  risk_label?: string;
  page?: number;
  size?: number;
}

export function usePredictions(filters: Filters = {}) {
  const [data, setData] = useState<PaginatedResponse<Prediction> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    api
      .get("/predictions", { params: filters, signal: controller.signal })
      .then((res) => setData(res.data))
      .catch((err) => {
        if (err.name !== "CanceledError") setError(err.message);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [JSON.stringify(filters)]);

  return { data, loading, error };
}
