import { useEffect, useState, useCallback } from "react";
import { supabase } from "../supabaseClient";

export default function HistoryPanel({ user, refreshKey }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from("messages")
      .select("*")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(20);
    if (error) console.error(error);
    setItems(data || []);
    setLoading(false);
  }, [user.id]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  return (
    <div className="history-section">
      <h2>Your past questions</h2>
      {loading && <div className="history-empty">Loading…</div>}
      {!loading && items.length === 0 && (
        <div className="history-empty">
          Nothing yet — ask Qobo something out loud to get started.
        </div>
      )}
      {items.map((item) => (
        <div className="history-item" key={item.id}>
          <div className="q">{item.question}</div>
          <div className="a">{item.answer}</div>
          <div className="meta">
            {new Date(item.created_at).toLocaleString()} ·{" "}
            {item.source === "refused" ? "declined (off-topic)" : "answered"}
          </div>
        </div>
      ))}
    </div>
  );
}
