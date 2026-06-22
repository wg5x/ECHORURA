import React, { useMemo, useState } from "react";
import { FileText, Loader2, Mic2, Play, Upload, Wand2 } from "lucide-react";
import type { PodcastAudioResult, PodcastDraft } from "../app/types";
import { PODCAST_HOST_OPTIONS } from "../domain/podcast/podcastConfig";
import { createPodcastAudio, createPodcastDraft } from "../lib/runtimeApi";

type PodcastVoice = (typeof PODCAST_HOST_OPTIONS)[number];

type PodcastStudioProps = {
  hostA: string;
  hostB: string;
  style: string;
  userId?: string;
};

function compactReportName(value: string) {
  return value.replace(/\.[^.]+$/, "").replace(/[_-]+/g, " ").trim().slice(0, 28);
}

function getRoundSpeakerLabel(speaker: string, firstVoice: PodcastVoice, secondVoice: PodcastVoice) {
  if (speaker === "host_a") return firstVoice.label;
  if (speaker === "host_b") return secondVoice.label;
  return speaker;
}

export function PodcastStudio({ hostA, hostB, style, userId }: PodcastStudioProps) {
  const [topic, setTopic] = useState("");
  const [reportText, setReportText] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(6);
  const [draft, setDraft] = useState<PodcastDraft | null>(null);
  const [audio, setAudio] = useState<PodcastAudioResult | null>(null);
  const [status, setStatus] = useState<"idle" | "reading" | "generating" | "ready" | "error">("idle");
  const [audioStatus, setAudioStatus] = useState<"idle" | "synthesizing" | "ready" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);

  const firstVoice = PODCAST_HOST_OPTIONS.find((voice) => voice.id === hostA) ?? PODCAST_HOST_OPTIONS[0];
  const secondVoice = PODCAST_HOST_OPTIONS.find((voice) => voice.id === hostB) ?? PODCAST_HOST_OPTIONS[1];
  const canGenerate = reportText.trim().length > 0 && firstVoice.id !== secondVoice.id && status !== "generating";

  const draftStats = useMemo(() => {
    if (!draft) return null;
    const chars = draft.rounds.reduce((total, round) => total + round.text.length, 0);
    return {
      chars,
      rounds: draft.rounds.length,
    };
  }, [draft]);

  async function handleReportFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const filename = file.name.toLowerCase();
    const isTextFile =
      file.type.startsWith("text/")
      || filename.endsWith(".md")
      || filename.endsWith(".txt")
      || filename.endsWith(".json")
      || filename.endsWith(".csv");

    if (!isTextFile) {
      setError("当前先支持 txt、md、json、csv 文本报告。");
      setStatus("error");
      event.target.value = "";
      return;
    }

    setStatus("reading");
    setError(null);
    try {
      const text = await file.text();
      setReportText(text.slice(0, 12000));
      setTopic((current) => current || compactReportName(file.name));
      setDraft(null);
      setAudio(null);
      setAudioStatus("idle");
      setStatus("idle");
    } catch {
      setError("报告读取失败，请换一个文本文件。");
      setStatus("error");
    } finally {
      event.target.value = "";
    }
  }

  async function generatePodcastDraft() {
    if (!canGenerate) return;

    setStatus("generating");
    setError(null);
    try {
      const nextDraft = await createPodcastDraft({
        topic: topic.trim() || "报告解读",
        sourceText: reportText,
        durationMinutes,
        content: `${style}\n${reportText}`,
        userId,
      });
      setDraft(nextDraft);
      setAudio(null);
      setAudioStatus("idle");
      setStatus("ready");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "无法生成播客轮次。");
      setStatus("error");
    }
  }

  async function generatePodcastAudio() {
    if (!draft || audioStatus === "synthesizing") return;

    setAudioStatus("synthesizing");
    setAudioError(null);
    try {
      const nextAudio = await createPodcastAudio({
        hostA: firstVoice.id,
        hostB: secondVoice.id,
        rounds: draft.rounds,
        title: draft.title,
        userId,
      });
      setAudio(nextAudio);
      setAudioStatus(nextAudio.audioUrl ? "ready" : "error");
      if (!nextAudio.audioUrl) {
        setAudioError(nextAudio.warnings[0] ?? "播客音频尚未生成。");
      }
    } catch (nextError) {
      setAudio(null);
      setAudioStatus("error");
      setAudioError(nextError instanceof Error ? nextError.message : "无法生成播客音频。");
    }
  }

  return (
    <section className="podcast-studio" aria-label="语音播客">
      <div className="podcast-header">
        <div>
          <span>{style || "doubao-seed-podcast"}</span>
          <h2>语音播客</h2>
        </div>
        <button className="podcast-start-button" type="button" disabled={!canGenerate} onClick={() => void generatePodcastDraft()}>
          {status === "generating" ? <Loader2 size={18} className="spin-icon" /> : <Play size={18} />}
          生成轮次
        </button>
      </div>

      <div className="podcast-workspace">
        <section className="podcast-input-panel" aria-label="播客输入">
          <label className="podcast-field">
            <span>标题</span>
            <input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="报告解读" />
          </label>

          <div className="podcast-pair-preview configured" aria-label="已绑定主持人音色">
            <span>
              <Mic2 size={16} />
              {firstVoice.label} · {firstVoice.description}
            </span>
            <span>
              <Mic2 size={16} />
              {secondVoice.label} · {secondVoice.description}
            </span>
          </div>

          <label className="podcast-upload">
            <Upload size={18} />
            <span>{status === "reading" ? "读取报告中" : "上传报告"}</span>
            <input type="file" accept=".txt,.md,.json,.csv,text/plain,text/markdown,application/json" onChange={handleReportFile} />
          </label>

          <label className="podcast-field">
            <span>报告内容</span>
            <textarea
              value={reportText}
              onChange={(event) => {
                setReportText(event.target.value);
                setDraft(null);
              }}
              placeholder="粘贴报告正文，或上传文本报告。"
            />
          </label>

          <label className="podcast-duration">
            <span>时长</span>
            <input
              type="range"
              min="2"
              max="20"
              value={durationMinutes}
              onChange={(event) => setDurationMinutes(Number(event.target.value))}
            />
            <strong>{durationMinutes} 分钟</strong>
          </label>

          {error ? <p className="podcast-error">{error}</p> : null}
        </section>

        <section className="podcast-preview-panel" aria-label="播客轮次预览">
          <div className="podcast-preview-header">
            <div>
              <FileText size={18} />
              <strong>{draft?.title ?? "等待报告"}</strong>
            </div>
            {draftStats ? <span>{draftStats.rounds} 轮 · {draftStats.chars} 字</span> : <span>未生成</span>}
          </div>

          {draft ? (
            <>
              <p className="podcast-summary">{draft.sourceSummary}</p>
              <div className="podcast-round-list">
                {draft.rounds.map((round) => (
                  <article className="podcast-round" key={round.idx}>
                    <span>{round.idx}</span>
                    <div>
                      <strong>{getRoundSpeakerLabel(round.speaker, firstVoice, secondVoice)}</strong>
                      <p>{round.text}</p>
                    </div>
                  </article>
                ))}
              </div>
              <div className="podcast-synthesis-note">
                <span>action = {draft.synthesis.recommendedAction} · nlp_texts · {draft.synthesis.maxRoundChars} 字以内</span>
                <button type="button" onClick={() => void generatePodcastAudio()} disabled={audioStatus === "synthesizing"}>
                  {audioStatus === "synthesizing" ? <Loader2 size={16} className="spin-icon" /> : <Wand2 size={16} />}
                  确认并生成音频
                </button>
              </div>
              {audio?.audioUrl ? (
                <div className="podcast-player">
                  <audio controls src={audio.audioUrl} />
                </div>
              ) : null}
              {audioError ? <p className="podcast-error">{audioError}</p> : null}
              {audio?.payload ? (
                <details className="podcast-payload-preview">
                  <summary>查看 action=3 请求参数</summary>
                  <pre>{JSON.stringify(audio.payload, null, 2)}</pre>
                </details>
              ) : null}
            </>
          ) : (
            <div className="podcast-empty">
              <FileText size={34} />
              <span>上传报告后生成播客轮次</span>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
