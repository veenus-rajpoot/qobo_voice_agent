import { useRef, useState } from "react";
import { supabase } from "../supabaseClient";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1;
  window.speechSynthesis.speak(utter);
}

export default function MicRecorder({ user, onNewMessage }) {
  const [state, setState] = useState("idle"); // idle | recording | thinking
  const [transcript, setTranscript] = useState("");
  const [answer, setAnswer] = useState(null); // { text, source }
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);

  const startRecording = async () => {
    setAnswer(null);
    setTranscript("");
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => chunksRef.current.push(e.data);
    recorder.onstop = () => handleStop(stream);
    recorder.start();
    mediaRecorderRef.current = recorder;
    setState("recording");
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
  };

  const handleStop = async (stream) => {
    stream.getTracks().forEach((t) => t.stop());
    setState("thinking");
    try {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const form = new FormData();
      form.append("audio", blob, "speech.webm");

      const sttRes = await fetch(`${BACKEND_URL}/api/stt`, {
        method: "POST",
        body: form,
      });
      const sttData = await sttRes.json();
      if (!sttRes.ok) throw new Error(sttData.error || "Transcription failed");
      const text = sttData.transcript?.trim();
      setTranscript(text);

      if (!text) {
        setAnswer({ text: "I didn't catch that. Try again?", source: "refused" });
        setState("idle");
        return;
      }

      const chatRes = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: text }),
      });
      const chatData = await chatRes.json();
      if (!chatRes.ok) throw new Error(chatData.error || "Chat failed");

      setAnswer({ text: chatData.answer, source: chatData.source });
      speak(chatData.answer);

      const { error } = await supabase.from("messages").insert({
        user_id: user.id,
        question: text,
        answer: chatData.answer,
        source: chatData.source,
      });
      if (error) console.error("Failed to save history:", error);
      onNewMessage?.();
    } catch (err) {
      console.error(err);
      setAnswer({ text: "Something went wrong. Please try again.", source: "refused" });
    } finally {
      setState("idle");
    }
  };

  const onMicClick = () => {
    if (state === "recording") stopRecording();
    else if (state === "idle") startRecording();
  };

  const statusLabel = {
    idle: "Tap to ask about Qobo",
    recording: "Listening — tap to stop",
    thinking: "Thinking…",
  }[state];

  return (
    <div className="mic-stage">
      <button
        className={`mic-button ${state === "recording" ? "recording" : ""}`}
        onClick={onMicClick}
        disabled={state === "thinking"}
        aria-label={state === "recording" ? "Stop recording" : "Start recording"}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z" />
          <path d="M19 11a7 7 0 0 1-14 0" strokeLinecap="round" />
          <path d="M12 18v3" strokeLinecap="round" />
        </svg>
      </button>
      <div className="mic-status">{statusLabel}</div>

      {transcript && (
        <div className="transcript">
          <div className="label">You asked</div>
          <div>{transcript}</div>
        </div>
      )}

      {answer && (
        <div className={`answer ${answer.source === "refused" ? "source-refused" : ""}`}>
          <div className={`label ${answer.source !== "refused" ? "source-tag" : ""}`}>
            {answer.source === "refused" ? "Outside Qobo topics" : "Qobo answer"}
          </div>
          <div>{answer.text}</div>
        </div>
      )}
    </div>
  );
}
