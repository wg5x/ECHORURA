import { useState, type ReactNode } from "react";
import { Eye, Pencil, Plus, X } from "lucide-react";
import type { CreateSceneInput } from "../app/types";
import { DEFAULT_PODCAST_PROFILE, PODCAST_HOST_OPTIONS } from "../domain/podcast/podcastConfig";
import { getSceneKindLabel, isPodcastSceneKind, SCENE_KIND_CONFIG } from "../domain/scene/sceneKindConfig";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import { buildScenePath } from "../domain/scene/sceneRoutes";
import { getCharacterManifest, getDefaultSpeaker, getModeVoiceOptions } from "../domain/voice/voiceOptions";

type AdminManagementPanelProps = {
  onCreateScene: (input: CreateSceneInput) => Promise<void>;
  onUpdateScene: (sceneId: string, input: CreateSceneInput) => Promise<void>;
  scenes: SceneTemplate[];
};

type ModalMode = "view" | "create" | "edit";
type ModalState = { mode: ModalMode; item?: SceneTemplate } | null;

const defaultSceneForm: CreateSceneInput = {
  id: "",
  sceneKind: "dialogue",
  mode: "o2",
  speaker: getDefaultSpeaker("o2"),
  botName: "",
  title: "",
  subtitle: "",
  audience: "",
  conversationGuide: "",
  interviewOutline: "",
  openingLine: "",
  systemRole: "",
  speakingStyle: "",
  characterManifest: "",
  podcastHostA: DEFAULT_PODCAST_PROFILE.hostA,
  podcastHostB: DEFAULT_PODCAST_PROFILE.hostB,
  podcastStyle: DEFAULT_PODCAST_PROFILE.style,
};

export function AdminManagementPanel({ onCreateScene, onUpdateScene, scenes }: AdminManagementPanelProps) {
  const [modal, setModal] = useState<ModalState>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function openModal(nextModal: ModalState) {
    setMessage(null);
    setModal(nextModal);
  }

  async function submitScene(sceneId: string | null, input: CreateSceneInput) {
    setSaving(true);
    setMessage(null);
    try {
      if (sceneId) {
        await onUpdateScene(sceneId, input);
        setMessage("场景已修改。");
      } else {
        await onCreateScene(input);
        setMessage("场景已创建。");
      }
      setModal(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : sceneId ? "无法修改场景。" : "无法创建场景。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="admin-management-panel" aria-label="场景管理">
      <div className="admin-panel-header">
        <div>
          <span className="section-title">场景管理</span>
          <p>场景是唯一入口。通过 sceneKind 和 sceneId 生成链接，按类型打开聊天或播客。</p>
        </div>
        <button className="primary-action compact" type="button" onClick={() => openModal({ mode: "create" })}>
          <Plus size={16} />
          新建场景
        </button>
      </div>

      <div className="admin-table" role="table" aria-label="场景列表">
        <div className="admin-table-row header" role="row">
          <span>名称</span>
          <span>类型</span>
          <span>路由</span>
          <span>操作</span>
        </div>
        {scenes.map((scene) => (
          <div className="admin-table-row" role="row" key={scene.id}>
            <span>
              <strong>{scene.title}</strong>
              <small>{scene.id}</small>
            </span>
            <span>{getSceneKindLabel(scene.sceneKind)}</span>
            <span>{buildScenePath(scene)}</span>
            <RowActions onEdit={() => openModal({ mode: "edit", item: scene })} onView={() => openModal({ mode: "view", item: scene })} />
          </div>
        ))}
      </div>

      {message ? <div className={message.includes("无法") ? "admin-message error" : "admin-message"}>{message}</div> : null}

      {modal ? (
        <AdminModal onClose={() => setModal(null)} title={modalTitle(modal)}>
          <SceneModalContent
            mode={modal.mode}
            scene={modal.item}
            saving={saving}
            onSubmit={(input) => void submitScene(modal.mode === "edit" && modal.item ? modal.item.id : null, input)}
          />
        </AdminModal>
      ) : null}
    </section>
  );
}

function RowActions({ onEdit, onView }: { onEdit: () => void; onView: () => void }) {
  return (
    <span className="admin-row-actions">
      <button type="button" onClick={onView}>
        <Eye size={15} />
        查看
      </button>
      <button type="button" onClick={onEdit}>
        <Pencil size={15} />
        修改
      </button>
    </span>
  );
}

function AdminModal({ children, onClose, title }: { children: ReactNode; onClose: () => void; title: string }) {
  return (
    <div className="admin-modal-backdrop" role="presentation">
      <section className="admin-modal" role="dialog" aria-modal="true" aria-label={title}>
        <header>
          <h3>{title}</h3>
          <button type="button" aria-label="关闭" onClick={onClose}>
            <X size={18} />
          </button>
        </header>
        {children}
      </section>
    </div>
  );
}

function SceneModalContent({
  mode,
  onSubmit,
  saving,
  scene,
}: {
  mode: ModalMode;
  onSubmit: (input: CreateSceneInput) => void;
  saving: boolean;
  scene?: SceneTemplate;
}) {
  const [form, setForm] = useState<CreateSceneInput>(() => scene ? sceneToForm(scene) : defaultSceneForm);
  const readonly = mode === "view";
  const isPodcast = isPodcastSceneKind(form.sceneKind);
  const modeVoiceOptions = getModeVoiceOptions(form.mode);

  return (
    <div className="admin-modal-body">
      <div className="modal-grid two">
        <label className="field">
          <span>场景类型</span>
          <select
            disabled={readonly}
            value={form.sceneKind}
            onChange={(event) => setForm((current) => ({ ...current, sceneKind: event.target.value as CreateSceneInput["sceneKind"] }))}
          >
            {Object.entries(SCENE_KIND_CONFIG).map(([sceneKind, option]) => (
              <option value={sceneKind} key={sceneKind}>{option.label}</option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>场景 ID</span>
          <input disabled={readonly || mode === "edit"} value={form.id} onChange={(event) => setForm((current) => ({ ...current, id: event.target.value }))} />
        </label>
      </div>
      <label className="field">
        <span>场景名称</span>
        <input disabled={readonly} value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} />
      </label>
      <label className="field">
        <span>副标题</span>
        <input disabled={readonly} value={form.subtitle} onChange={(event) => setForm((current) => ({ ...current, subtitle: event.target.value }))} />
      </label>
      <label className="field">
        <span>适用对象</span>
        <input disabled={readonly} value={form.audience} onChange={(event) => setForm((current) => ({ ...current, audience: event.target.value }))} />
      </label>
      <label className="field">
        <span>场景说明</span>
        <textarea disabled={readonly} value={form.conversationGuide} onChange={(event) => setForm((current) => ({ ...current, conversationGuide: event.target.value }))} />
      </label>
      {isPodcast ? (
        <div className="modal-grid two">
          <PodcastHostField disabled={readonly} label="主持人 A" value={form.podcastHostA} onChange={(value) => setForm((current) => ({ ...current, podcastHostA: value }))} />
          <PodcastHostField disabled={readonly} label="主持人 B" value={form.podcastHostB} onChange={(value) => setForm((current) => ({ ...current, podcastHostB: value }))} />
          <label className="field wide">
            <span>播客风格</span>
            <input disabled={readonly} value={form.podcastStyle} onChange={(event) => setForm((current) => ({ ...current, podcastStyle: event.target.value }))} />
          </label>
        </div>
      ) : (
        <>
          <div className="modal-grid two">
            <label className="field">
              <span>模型模式</span>
              <select
                disabled={readonly}
                value={form.mode}
                onChange={(event) => {
                  const nextMode = event.target.value as CreateSceneInput["mode"];
                  const nextSpeaker = getDefaultSpeaker(nextMode);
                  setForm((current) => ({
                    ...current,
                    mode: nextMode,
                    speaker: nextSpeaker,
                    characterManifest: nextMode === "sc2" ? getCharacterManifest(nextSpeaker) : "",
                  }));
                }}
              >
                <option value="o2">O2 实时语音</option>
                <option value="sc2">SC2 角色扮演</option>
              </select>
            </label>
            <label className="field">
              <span>音色</span>
              <select
                disabled={readonly}
                value={form.speaker}
                onChange={(event) => {
                  const nextSpeaker = event.target.value;
                  setForm((current) => ({
                    ...current,
                    speaker: nextSpeaker,
                    characterManifest: current.mode === "sc2" ? getCharacterManifest(nextSpeaker) : current.characterManifest,
                  }));
                }}
              >
                {modeVoiceOptions.map((option) => (
                  <option value={option.id} key={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="field">
            <span>基础人设</span>
            <input disabled={readonly} value={form.botName} onChange={(event) => setForm((current) => ({ ...current, botName: event.target.value }))} />
          </label>
          <label className="field">
            <span>开场白</span>
            <textarea disabled={readonly} value={form.openingLine} onChange={(event) => setForm((current) => ({ ...current, openingLine: event.target.value }))} />
          </label>
          <label className="field">
            <span>访谈内容</span>
            <textarea disabled={readonly} className="tall" value={form.interviewOutline} onChange={(event) => setForm((current) => ({ ...current, interviewOutline: event.target.value }))} />
          </label>
          {form.mode === "sc2" ? (
            <label className="field">
              <span>角色描述</span>
              <textarea disabled={readonly} className="tall" value={form.characterManifest} onChange={(event) => setForm((current) => ({ ...current, characterManifest: event.target.value }))} />
            </label>
          ) : (
            <>
              <label className="field">
                <span>系统人设</span>
                <textarea disabled={readonly} className="tall" value={form.systemRole} onChange={(event) => setForm((current) => ({ ...current, systemRole: event.target.value }))} />
              </label>
              <label className="field">
                <span>对话风格</span>
                <textarea disabled={readonly} value={form.speakingStyle} onChange={(event) => setForm((current) => ({ ...current, speakingStyle: event.target.value }))} />
              </label>
            </>
          )}
        </>
      )}
      {readonly ? null : (
        <button className="primary-action" type="button" disabled={saving || !form.title.trim()} onClick={() => onSubmit(form)}>
          {saving ? "保存中" : mode === "edit" ? "保存修改" : "创建场景"}
        </button>
      )}
    </div>
  );
}

function PodcastHostField({ disabled, label, onChange, value }: { disabled: boolean; label: string; onChange: (value: string) => void; value: string }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)}>
        {PODCAST_HOST_OPTIONS.map((option) => (
          <option value={option.id} key={option.id}>{option.label}</option>
        ))}
      </select>
    </label>
  );
}

function modalTitle(modal: NonNullable<ModalState>) {
  const action = modal.mode === "view" ? "查看" : modal.mode === "edit" ? "修改" : "创建";
  return `${action}场景`;
}

function sceneToForm(scene: SceneTemplate): CreateSceneInput {
  return {
    id: scene.id,
    sceneKind: scene.sceneKind,
    mode: scene.config.mode,
    speaker: scene.config.speaker,
    botName: scene.config.botName,
    title: scene.title,
    subtitle: scene.subtitle,
    audience: scene.audience,
    conversationGuide: scene.conversationGuide,
    interviewOutline: scene.config.interviewOutline,
    openingLine: scene.config.openingLine,
    systemRole: scene.config.systemRole,
    speakingStyle: scene.config.speakingStyle,
    characterManifest: scene.config.characterManifest,
    podcastHostA: scene.config.podcastHostA || scene.podcastProfile?.hostA || DEFAULT_PODCAST_PROFILE.hostA,
    podcastHostB: scene.config.podcastHostB || scene.podcastProfile?.hostB || DEFAULT_PODCAST_PROFILE.hostB,
    podcastStyle: scene.config.podcastStyle || scene.podcastProfile?.style || DEFAULT_PODCAST_PROFILE.style,
  };
}
