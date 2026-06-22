import { CircleHelp, Layers3, Sparkles } from "lucide-react";

type HeaderBarProps = {
  apiEnabled: boolean;
  embedded?: boolean;
  inCall: boolean;
  onManageScenes: () => void;
  onOpenApi: () => void;
  sceneManagementOpen: boolean;
  showUsage?: boolean;
  title?: string;
  tokens: number | null;
};

export function HeaderBar({
  apiEnabled,
  embedded = false,
  inCall,
  onManageScenes,
  onOpenApi,
  sceneManagementOpen,
  showUsage = true,
  title = "AI Engine 场景控制台",
  tokens,
}: HeaderBarProps) {
  return (
    <header className={inCall ? "topbar call-topbar" : "topbar"}>
      <div>
        <h1>{title}</h1>
      </div>
      <div className="header-actions">
        {showUsage ? (
          <button className="token-pill" type="button">
            <Sparkles size={15} />
            {tokens === null ? "用量待返回" : `${tokens.toLocaleString("zh-CN")} Token(s)`}
            <CircleHelp size={15} />
          </button>
        ) : null}
        {apiEnabled && !embedded ? (
          <button className="api-button" type="button" onClick={onOpenApi}>
            API 调用
          </button>
        ) : null}
        {!embedded ? (
          <button className="api-button" type="button" onClick={onManageScenes} disabled={inCall}>
            <Layers3 size={15} />
            {sceneManagementOpen ? "返回场景" : "场景管理"}
          </button>
        ) : null}
      </div>
    </header>
  );
}
