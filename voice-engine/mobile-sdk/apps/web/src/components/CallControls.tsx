import { Mic, MicOff, Octagon, Power } from "lucide-react";

type CallControlsProps = {
  elapsedText: string;
  microphoneEnabled: boolean;
  onEndCall: () => void;
  onInterrupt: () => void;
  onToggleMicrophone: () => void;
  onToggleRecording: () => void;
  recordingEnabled: boolean;
  recordingToggleVisible?: boolean;
  statusLabel: string;
};

export function CallControls({
  elapsedText,
  microphoneEnabled,
  onEndCall,
  onInterrupt,
  onToggleMicrophone,
  onToggleRecording,
  recordingEnabled,
  recordingToggleVisible = true,
  statusLabel,
}: CallControlsProps) {
  return (
    <div className="call-control">
      <div className="control-status">
        <span className="live-dot" />
        <strong>{statusLabel}</strong>
        <time>{elapsedText}</time>
      </div>
      <div className="control-actions">
        <button
          className={microphoneEnabled ? "icon-control" : "icon-control muted"}
          type="button"
          aria-label={microphoneEnabled ? "静音并停止播报" : "恢复语音输入和播报"}
          title={microphoneEnabled ? "静音并停止播报" : "恢复语音输入和播报"}
          data-testid="microphone-toggle"
          data-microphone-enabled={microphoneEnabled}
          onClick={onToggleMicrophone}
        >
          {microphoneEnabled ? <Mic size={18} /> : <MicOff size={18} />}
        </button>
        <span>{microphoneEnabled ? "静音" : "恢复"}</span>
        <i />
        <button
          className="icon-control interrupt"
          type="button"
          aria-label="实时打断当前播报"
          title="实时打断当前播报"
          data-testid="interrupt-button"
          onClick={onInterrupt}
        >
          <Octagon size={18} />
        </button>
        <span>打断</span>
        {recordingToggleVisible ? (
          <>
            <i />
            <span>日志</span>
            <button
              className={recordingEnabled ? "switch active" : "switch"}
              type="button"
              role="switch"
              aria-checked={recordingEnabled}
              aria-label={recordingEnabled ? "关闭日志" : "开启日志"}
              title={recordingEnabled ? "关闭日志" : "开启日志"}
              data-testid="recording-toggle"
              data-recording-enabled={recordingEnabled}
              onClick={onToggleRecording}
            >
              <span />
            </button>
          </>
        ) : null}
        <i />
        <button className="power-button" type="button" aria-label="结束语音对话" onClick={onEndCall}>
          <Power size={19} />
        </button>
      </div>
    </div>
  );
}
