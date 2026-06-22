import { X } from "lucide-react";
import type { PayloadPreview } from "../app/types";

type ApiDrawerProps = {
  onClose: () => void;
  preview: PayloadPreview | null;
};

export function ApiDrawer({ onClose, preview }: ApiDrawerProps) {
  return (
    <div className="api-drawer" role="dialog" aria-modal="true" aria-label="API 调用参数">
      <div className="api-panel">
        <div className="api-panel-header">
          <div>
            <strong>API 调用参数</strong>
            <span>当前通话走 openspeech WebSocket；这里展示实际发送的 StartSession 参数。</span>
          </div>
          <button type="button" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        {preview?.warnings?.length ? (
          <div className="api-warnings">
            {preview.warnings.map((warning) => (
              <span key={warning}>{warning}</span>
            ))}
          </div>
        ) : null}
        <div className="api-preview-scroll">
          <section className="api-preview-block">
            <h3>openspeech StartSession</h3>
            <pre>{preview ? JSON.stringify(preview.payload, null, 2) : "正在生成..."}</pre>
          </section>
        </div>
      </div>
    </div>
  );
}
