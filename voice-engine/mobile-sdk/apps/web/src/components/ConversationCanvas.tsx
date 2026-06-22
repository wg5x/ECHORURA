import { useEffect, useRef } from "react";
import type { VoiceEvent } from "@ai-engine/shared";
import { formatVoiceEventText } from "../lib/eventUtils";

type ConversationCanvasProps = {
  assistantFallback: string;
  conversationGuide: string;
  eventCount: number;
  events: VoiceEvent[];
  latestSystemEvent?: VoiceEvent;
  sceneTitle: string;
  transcriptCue: string;
};

export function ConversationCanvas({
  assistantFallback,
  conversationGuide,
  eventCount,
  events,
  latestSystemEvent,
  sceneTitle,
  transcriptCue,
}: ConversationCanvasProps) {
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [eventCount, latestSystemEvent?.id, transcriptCue]);

  return (
    <div
      className="conversation-canvas"
      data-testid="record-panel"
      data-recording-enabled
      data-event-count={eventCount}
    >
      <p className="conversation-intro">
        当前场景：{sceneTitle}。{conversationGuide}
      </p>
      <div className="conversation-stream" aria-live="polite">
        {events.length ? (
          events.map((event) => (
            <article className={`chat-message ${event.type === "asr" ? "user" : "assistant"}`} key={event.id}>
              <p>{formatVoiceEventText(event.text)}</p>
              <time>{event.at}</time>
            </article>
          ))
        ) : (
          <article className="chat-message assistant">
            <p>{assistantFallback || "在呢，你想和我聊点什么呢？"}</p>
          </article>
        )}
        <div ref={endRef} aria-hidden="true" />
      </div>
      {latestSystemEvent ? (
        <div className="conversation-system">{formatVoiceEventText(latestSystemEvent.text)}</div>
      ) : null}
      <div className="transcript-cue">{transcriptCue}</div>
    </div>
  );
}
