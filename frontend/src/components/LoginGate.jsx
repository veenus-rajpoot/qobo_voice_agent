import { supabase } from "../supabaseClient";

export default function LoginGate() {
  const signIn = () => {
    supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
  };

  return (
    <div className="login-gate">
      <div className="display">Talk to Qobo</div>
      <p>
        Sign in to ask about pricing, plans, or how Qobo builds your business
        on WhatsApp — and pick up right where you left off.
      </p>
      <button className="google-btn" onClick={signIn}>
        Continue with Google
      </button>
    </div>
  );
}