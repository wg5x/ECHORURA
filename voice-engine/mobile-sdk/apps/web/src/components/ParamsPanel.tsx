import type { Dispatch, SetStateAction } from "react";
import { BookOpen, Bot, Brain, ChevronRight, Headphones, RefreshCw, Save, Settings2, Trash2, Volume2 } from "lucide-react";
import type { ModelMode, RealtimeConfig, WebSearchType } from "@ai-engine/shared";
import type {
  CallLogEntry,
  CreateRoleInput,
  CreateSceneInput,
  CreateUserInput,
  MemoryCard,
  MemoryStatus,
  RuntimeRole,
  VoiceOption,
} from "../app/types";
import { AdminManagementPanel } from "./AdminManagementPanel";
import { getMemoryPolicy, getReportPolicy, getSafetyPolicy } from "../domain/policy/policyRegistry";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import type { TestUserProfile } from "../domain/user/testUsers";
import { getCharacterManifest, getDefaultSpeaker } from "../domain/voice/voiceOptions";

const modeCards: Array<{
  mode: ModelMode;
  title: string;
  subtitle: string;
  icon: typeof Headphones;
}> = [
  {
    mode: "o2",
    title: "默认模式",
    subtitle: "O2.0 实时语音",
    icon: Headphones,
  },
  {
    mode: "sc2",
    title: "角色扮演",
    subtitle: "SC2.0 强人设",
    icon: Bot,
  },
];

type ParamsPanelProps = {
  avatarVideoKey: string;
  avatarVideoUrl: string;
  canManageScenes: boolean;
  config: RealtimeConfig;
  configDirty: boolean;
  configSaveError: string | null;
  configSaving: boolean;
  callLogError: string | null;
  callLogs: CallLogEntry[];
  callLogStatus: "idle" | "loading" | "saving" | "saved" | "error";
  memoryAutoCompress: boolean;
  memoryCard: MemoryCard | null;
  memoryEnabled: boolean;
  memoryError: string | null;
  memoryInjected: boolean;
  memoryMaxChars: number;
  memoryPreviewItems: string[];
  memoryStatus: MemoryStatus;
  memoryStatusText: string;
  memoryWarnings: string[];
  modeVoiceOptions: VoiceOption[];
  model: string;
  onClearMemoryCard: () => void | Promise<void>;
  onCreateRole: (input: CreateRoleInput) => Promise<void>;
  onCreateScene: (input: CreateSceneInput) => Promise<void>;
  onCreateUser: (input: CreateUserInput) => Promise<void>;
  onUpdateRole: (roleId: string, input: CreateRoleInput) => Promise<void>;
  onUpdateScene: (sceneId: string, input: CreateSceneInput) => Promise<void>;
  onUpdateUser: (userId: string, input: CreateUserInput) => Promise<void>;
  onLoadMemoryCard: () => void | Promise<MemoryCard | null>;
  onLoadCallLogs: () => void | Promise<CallLogEntry[]>;
  onOpenApiDrawer: () => void;
  onPreviewVoice: () => void | Promise<void>;
  onSaveSceneConfig: () => void | Promise<void>;
  onSelectTestUser: (profile: TestUserProfile) => void;
  selectedScene: SceneTemplate;
  selectedUser: TestUserProfile;
  setConfig: Dispatch<SetStateAction<RealtimeConfig>>;
  setMemoryAutoCompress: (enabled: boolean) => void;
  setMemoryEnabled: (enabled: boolean) => void;
  setMemoryMaxChars: (maxChars: number) => void;
  speaker: string;
  runtimeScenes: SceneTemplate[];
  roles: RuntimeRole[];
  userProfiles: TestUserProfile[];
  voiceLabel: string;
  voicePreviewing: boolean;
};

export function ParamsPanel({
  avatarVideoKey,
  avatarVideoUrl,
  canManageScenes,
  config,
  configDirty,
  configSaveError,
  configSaving,
  callLogError,
  callLogs,
  callLogStatus,
  memoryAutoCompress,
  memoryCard,
  memoryEnabled,
  memoryError,
  memoryInjected,
  memoryMaxChars,
  memoryPreviewItems,
  memoryStatus,
  memoryStatusText,
  memoryWarnings,
  modeVoiceOptions,
  model,
  onClearMemoryCard,
  onCreateRole,
  onCreateScene,
  onCreateUser,
  onUpdateRole,
  onUpdateScene,
  onUpdateUser,
  onLoadMemoryCard,
  onLoadCallLogs,
  onOpenApiDrawer,
  onPreviewVoice,
  onSaveSceneConfig,
  onSelectTestUser,
  selectedScene,
  selectedUser,
  setConfig,
  setMemoryAutoCompress,
  setMemoryEnabled,
  setMemoryMaxChars,
  speaker,
  runtimeScenes,
  roles,
  userProfiles,
  voiceLabel,
  voicePreviewing,
}: ParamsPanelProps) {
  const selectedSafetyPolicy = getSafetyPolicy(selectedScene.safetyPolicy);
  const selectedMemoryPolicy = getMemoryPolicy(selectedScene.memoryPolicy);
  const selectedReportPolicy = getReportPolicy(selectedScene.reportPolicy);
  const roleLabel = roles.find((role) => role.id === selectedUser.role)?.name ?? selectedUser.role;

  return (
    <aside className="params-panel" aria-label="模型参数">
      <div className="panel-header">
        <h2>{canManageScenes ? "场景参数" : "场景信息"}</h2>
        <Settings2 size={18} />
      </div>

      <section className="selected-scene-summary" aria-label="当前场景">
        <div>
          <strong>{selectedScene.title}</strong>
          <span>{selectedScene.modelProfileId}</span>
        </div>
        <p>{selectedScene.subtitle}</p>
        <dl>
          <div>
            <dt>当前角色</dt>
            <dd>{roleLabel}</dd>
          </div>
          <div>
            <dt>安全策略</dt>
            <dd>{selectedSafetyPolicy?.title ?? selectedScene.safetyPolicy}</dd>
          </div>
          <div>
            <dt>记忆策略</dt>
            <dd>{selectedMemoryPolicy?.title ?? selectedScene.memoryPolicy}</dd>
          </div>
          <div>
            <dt>报告策略</dt>
            <dd>{selectedReportPolicy?.title ?? selectedScene.reportPolicy}</dd>
          </div>
        </dl>
      </section>

      <section className="test-user-panel" aria-label="测试用户">
        <div className="section-title">账号视角</div>
        <div className="test-user-grid">
          {userProfiles.map((profile) => (
            <button
              className={selectedUser.id === profile.id ? "test-user-card selected" : "test-user-card"}
              type="button"
              key={profile.id}
              onClick={() => onSelectTestUser(profile)}
              aria-pressed={selectedUser.id === profile.id}
            >
              <strong>{profile.name}</strong>
              <span>{roles.find((role) => role.id === profile.role)?.name ?? profile.role} · {profile.segment}</span>
            </button>
          ))}
        </div>
        <div className="policy-detail compact-policy">
          <strong>{selectedUser.name}</strong>
          <p>{selectedUser.traits.join("；")}</p>
          <small>
            已分配场景：
            {selectedUser.assignedSceneIds
              .map((sceneId) => runtimeScenes.find((scene) => scene.id === sceneId)?.title ?? sceneId)
              .join("、")}
          </small>
          <small>{selectedUser.constraints.join("；")}</small>
        </div>
      </section>

      {canManageScenes ? (
        <AdminManagementPanel
          onCreateScene={onCreateScene}
          onUpdateScene={onUpdateScene}
          scenes={runtimeScenes}
        />
      ) : null}

      <section className="memory-card-panel" aria-label="本地压缩记忆">
        <div className="memory-card-header">
          <span className="memory-card-icon">
            <Brain size={17} />
          </span>
          <div>
            <strong>本地压缩记忆</strong>
            <small>{selectedUser.name} / {selectedScene.title}</small>
          </div>
          <em className={`memory-status ${memoryInjected ? "active" : ""}`}>{memoryStatusText}</em>
        </div>

        <div className="memory-switch-grid">
          <label className="toggle-row">
            <input type="checkbox" checked={memoryEnabled} onChange={(event) => setMemoryEnabled(event.target.checked)} />
            下次通话注入
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={memoryAutoCompress}
              onChange={(event) => setMemoryAutoCompress(event.target.checked)}
            />
            会后自动压缩
          </label>
        </div>

        <label className="field memory-budget-field">
          <span>记忆预算 {memoryMaxChars} 字符</span>
          <input
            type="range"
            min={400}
            max={3000}
            step={100}
            value={memoryMaxChars}
            onChange={(event) => setMemoryMaxChars(Number(event.target.value))}
          />
        </label>

        <div className="memory-preview">
          {memoryPreviewItems.length ? (
            memoryPreviewItems.map((item) => <p key={item}>{item}</p>)
          ) : (
            <p>暂无可注入的记忆卡。结束一次有转写的通话后，会生成短摘要和待承接话题。</p>
          )}
        </div>

        {memoryWarnings.length ? <div className="memory-note">{memoryWarnings.join("；")}</div> : null}
        {memoryError ? <div className="memory-error">{memoryError}</div> : null}

        <div className="memory-actions">
          <button
            type="button"
            onClick={() => void onLoadMemoryCard()}
            disabled={memoryStatus === "loading" || memoryStatus === "compressing" || memoryStatus === "clearing"}
            title="刷新记忆卡"
          >
            <RefreshCw size={15} />
            刷新
          </button>
          <button
            type="button"
            onClick={() => void onClearMemoryCard()}
            disabled={!memoryCard || memoryStatus === "loading" || memoryStatus === "compressing" || memoryStatus === "clearing"}
            title="清空当前用户和场景的记忆卡"
          >
            <Trash2 size={15} />
            清空
          </button>
        </div>
      </section>

      <section className="call-log-panel" aria-label="访谈日志">
        <div className="memory-card-header">
          <span className="memory-card-icon">
            <BookOpen size={17} />
          </span>
          <div>
            <strong>访谈日志</strong>
            <small>{selectedUser.name} / {selectedScene.title}</small>
          </div>
          <em className={`memory-status ${callLogStatus === "saved" ? "active" : ""}`}>
            {callLogStatus === "loading" ? "读取中" : callLogStatus === "saving" ? "保存中" : callLogStatus === "saved" ? "已保存" : callLogs.length ? `${callLogs.length} 条` : "暂无"}
          </em>
        </div>
        <div className="call-log-list">
          {callLogs.length ? (
            callLogs.map((log) => (
              <article key={log.id}>
                <strong>{log.report.startedAt} - {log.report.endedAt}</strong>
                <p>{log.report.summary}</p>
                <small>
                  {log.report.userTurns}/{log.report.assistantTurns} 轮 · {log.report.durationSeconds}s
                </small>
              </article>
            ))
          ) : (
            <p>结束一次访谈后，会自动保存转写、摘要、轮次和性能指标。</p>
          )}
        </div>
        {callLogError ? <div className="memory-error">{callLogError}</div> : null}
        <div className="memory-actions">
          <button type="button" onClick={() => void onLoadCallLogs()} disabled={callLogStatus === "loading" || callLogStatus === "saving"}>
            <RefreshCw size={15} />
            刷新
          </button>
        </div>
      </section>

      <details className="policy-detail" open>
        <summary>安全策略内容</summary>
        <p>{selectedSafetyPolicy?.intent ?? selectedScene.safetyPolicy}</p>
        <ul>
          {(selectedSafetyPolicy?.rules ?? []).map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </details>

      <details className="policy-detail">
        <summary>记忆协议说明</summary>
        <ul>
          {(selectedMemoryPolicy?.rules ?? []).map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </details>

      <details className="policy-detail">
        <summary>报告策略</summary>
        <p>{selectedReportPolicy?.title ?? selectedScene.reportPolicy}</p>
        <ul>
          {(selectedReportPolicy?.sections ?? selectedScene.reportFocus).map((section) => (
            <li key={section}>{section}</li>
          ))}
        </ul>
      </details>

      {canManageScenes ? (
        <>
          <div className="mode-grid">
            {modeCards.map((card) => {
              const Icon = card.icon;
              return (
                <button
                  className={config.mode === card.mode ? "mode-card selected" : "mode-card"}
                  type="button"
                  key={card.title}
                  onClick={() => {
                    const nextSpeaker = getDefaultSpeaker(card.mode);
                    setConfig((current) => ({
                      ...current,
                      mode: card.mode,
                      speaker: nextSpeaker,
                      characterManifest: card.mode === "sc2" ? getCharacterManifest(nextSpeaker) : "",
                    }));
                  }}
                >
                  <Icon size={18} />
                  <span>
                    <strong>{card.title}</strong>
                    <small>{card.subtitle}</small>
                  </span>
                </button>
              );
            })}
          </div>

          <div className="field compact">
            <span>模型版本</span>
            <strong>{model}</strong>
          </div>

          <div className="section-title">场景调整</div>

          <div className="field">
            <span>音色</span>
            <div className="voice-card as-field">
              <span className="voice-avatar" aria-hidden="true">
                <video key={avatarVideoKey} src={avatarVideoUrl} muted playsInline preload="auto" />
              </span>
              <span className="voice-name">
                <strong>{voiceLabel}</strong>
                <small>{speaker || "需要填写音色 ID"}</small>
              </span>
              <button
                className={voicePreviewing ? "voice-preview-button loading" : "voice-preview-button"}
                type="button"
                aria-label={`试听 ${voiceLabel}`}
                aria-busy={voicePreviewing}
                disabled={!speaker || voicePreviewing}
                title={voicePreviewing ? "试听中" : "试听音色"}
                onClick={onPreviewVoice}
              >
                <Volume2 size={18} />
              </button>
            </div>
            <select
              value={config.speaker}
              onChange={(event) => {
                const nextSpeaker = event.target.value;
                setConfig((current) => ({
                  ...current,
                  speaker: nextSpeaker,
                  characterManifest: current.mode === "sc2" ? getCharacterManifest(nextSpeaker) : "",
                }));
              }}
              aria-label="选择音色"
            >
              {modeVoiceOptions.map((option) => (
                <option value={option.id} key={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <label className="field">
            <span>开场白</span>
            <textarea
              value={config.openingLine}
              onChange={(event) => setConfig((current) => ({ ...current, openingLine: event.target.value }))}
              placeholder="你好，快来和我语音对话吧!"
            />
          </label>

          <label className="field">
            <span>访谈内容</span>
            <textarea
              className="tall"
              value={config.interviewOutline}
              onChange={(event) => setConfig((current) => ({ ...current, interviewOutline: event.target.value }))}
              placeholder="填写访谈流程、样本甄别、必问问题和追问规则。"
            />
          </label>

          {config.mode === "o2" ? (
            <>
              <label className="field">
                <span>基础人设</span>
                <textarea
                  maxLength={20}
                  value={config.botName}
                  onChange={(event) => setConfig((current) => ({ ...current, botName: event.target.value }))}
                  placeholder="用于修改基础人设信息，例如人名、来源等，默认为豆包"
                />
              </label>

              <label className="field">
                <span>背景人设</span>
                <textarea
                  className="tall"
                  value={config.systemRole}
                  onChange={(event) => setConfig((current) => ({ ...current, systemRole: event.target.value }))}
                  placeholder="用于配置背景人设信息"
                />
              </label>

              <label className="field">
                <span>模型对话风格</span>
                <textarea
                  value={config.speakingStyle}
                  onChange={(event) => setConfig((current) => ({ ...current, speakingStyle: event.target.value }))}
                  placeholder="用于配置模型对话风格"
                />
              </label>
            </>
          ) : (
            <label className="field">
              <span>角色描述</span>
              <textarea
                className="tall"
                value={config.characterManifest}
                onChange={(event) => setConfig((current) => ({ ...current, characterManifest: event.target.value }))}
                placeholder="映射 dialog.character_manifest，只针对 SC2.0"
              />
            </label>
          )}

          <details className="advanced" open>
            <summary>
              高级设置
              <ChevronRight size={16} />
            </summary>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={config.enableWebSearch}
                onChange={(event) => setConfig((current) => ({ ...current, enableWebSearch: event.target.checked }))}
              />
              联网能力
            </label>

            {config.enableWebSearch ? (
              <div className="advanced-grid">
                <label className="field">
                  <span>联网类型</span>
                  <select
                    value={config.webSearchType}
                    onChange={(event) =>
                      setConfig((current) => ({
                        ...current,
                        webSearchType: event.target.value as WebSearchType,
                      }))
                    }
                  >
                    <option value="web">普通版 web</option>
                    <option value="web_summary">总结版 web_summary</option>
                    <option value="web_agent">搜索 Agent web_agent</option>
                  </select>
                </label>
                <label className="field">
                  <span>搜索结果数</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={config.webSearchResultCount}
                    onChange={(event) =>
                      setConfig((current) => ({
                        ...current,
                        webSearchResultCount: Math.min(10, Math.max(1, Number(event.target.value) || 1)),
                      }))
                    }
                  />
                </label>
                {config.webSearchType === "web_agent" ? (
                  <label className="field">
                    <span>搜索 Bot ID</span>
                    <input
                      value={config.webSearchBotId}
                      onChange={(event) => setConfig((current) => ({ ...current, webSearchBotId: event.target.value }))}
                      placeholder="映射 volc_websearch_bot_id"
                    />
                  </label>
                ) : null}
                <label className="field">
                  <span>无结果回复</span>
                  <input
                    value={config.webSearchNoResultMessage}
                    onChange={(event) =>
                      setConfig((current) => ({ ...current, webSearchNoResultMessage: event.target.value }))
                    }
                  />
                </label>
              </div>
            ) : null}

            <label className={config.mode === "sc2" ? "toggle-row disabled" : "toggle-row"}>
              <input
                type="checkbox"
                checked={config.enableMusic}
                disabled={config.mode === "sc2"}
                onChange={(event) => setConfig((current) => ({ ...current, enableMusic: event.target.checked }))}
              />
              唱歌能力
              <small>仅 O2.0 / model=1.2.1.1</small>
            </label>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={config.enableLoudnessNorm}
                onChange={(event) => setConfig((current) => ({ ...current, enableLoudnessNorm: event.target.checked }))}
              />
              响度均衡
            </label>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={config.enableUserQueryExit}
                onChange={(event) => setConfig((current) => ({ ...current, enableUserQueryExit: event.target.checked }))}
              />
              退出意图识别
            </label>

            <label className="toggle-row">
              <input
                type="checkbox"
                checked={config.enableBargeIn}
                onChange={(event) => setConfig((current) => ({ ...current, enableBargeIn: event.target.checked }))}
              />
              允许语音打断
            </label>

            <div className="range-grid">
              <label className="field">
                <span>语速 {config.speechRate}</span>
                <input
                  type="range"
                  min={-50}
                  max={100}
                  value={config.speechRate}
                  onChange={(event) => setConfig((current) => ({ ...current, speechRate: Number(event.target.value) }))}
                />
              </label>
              <label className="field">
                <span>音量 {config.loudnessRate}</span>
                <input
                  type="range"
                  min={-50}
                  max={100}
                  value={config.loudnessRate}
                  onChange={(event) => setConfig((current) => ({ ...current, loudnessRate: Number(event.target.value) }))}
                />
              </label>
            </div>
          </details>

          <div className="scene-config-actions">
            <button
              className="primary-action"
              type="button"
              onClick={() => void onSaveSceneConfig()}
              disabled={!configDirty || configSaving}
            >
              <Save size={16} />
              {configSaving ? "保存中" : configDirty ? "保存场景配置" : "已保存"}
            </button>
            {configSaveError ? <p>{configSaveError}</p> : null}
          </div>

          <button className="doc-link" type="button" onClick={onOpenApiDrawer}>
            <BookOpen size={16} />
            查看接入参数
          </button>
        </>
      ) : null}
    </aside>
  );
}
