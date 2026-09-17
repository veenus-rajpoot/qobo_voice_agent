import { useEffect, useState } from "react";
import { supabase } from "./supabaseClient";
import LoginGate from "./components/LoginGate";
import MicRecorder from "./components/MicRecorder";
import HistoryPanel from "./components/HistoryPanel";

export default function App() {
  const [session, setSession] = useState(null);
  const [checked, setChecked] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setChecked(true);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const signOut = () => supabase.auth.signOut();

  if (!checked) return null;

  return (
    <div className="app-shell">
      <div className="topbar">
        <div className="brand">
          <span className="display">Qobo</span>
          <span className="tag">voice agent</span>
        </div>
        <div className="auth-box">
          {session ? (
            <div className="user-pill">
              <img
                src={session.user.user_metadata?.avatar_url}
                alt=""
                referrerPolicy="no-referrer"
              />
              {session.user.user_metadata?.full_name || session.user.email}
              <button onClick={signOut}>Sign out</button>
            </div>
          ) : null}
        </div>
      </div>

      {!session ? (
        <LoginGate />
      ) : (
        <>
          <MicRecorder
            user={session.user}
            onNewMessage={() => setRefreshKey((k) => k + 1)}
          />
          <HistoryPanel user={session.user} refreshKey={refreshKey} />
        </>
      )}
    </div>
  );
}
