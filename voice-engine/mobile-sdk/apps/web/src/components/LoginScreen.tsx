import { LogIn, Play } from "lucide-react";
import type { RuntimeRole } from "../app/types";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import type { TestUserProfile } from "../domain/user/testUsers";
import { getLocalAvatarVideoUrl, getVoiceOption } from "../domain/voice/voiceOptions";

type LoginScreenProps = {
  error: string | null;
  loading: boolean;
  onLogin: (userId: string) => void | Promise<void>;
  onUseScene: (sceneId: SceneTemplate["id"]) => void | Promise<void>;
  roles: RuntimeRole[];
  scenes: SceneTemplate[];
  users: TestUserProfile[];
};

function getSceneCardTitle(scene: SceneTemplate) {
  return scene.title.replace(/\s*音色体验$/, "");
}

function playCardVideo(card: HTMLButtonElement) {
  const video = card.querySelector("video");
  if (!video) return;
  void video.play().catch(() => undefined);
}

function resetCardVideo(card: HTMLButtonElement) {
  const video = card.querySelector("video");
  if (!video) return;
  video.pause();
  video.currentTime = 0;
}

export function LoginScreen({ error, loading, onLogin, onUseScene, roles, scenes, users }: LoginScreenProps) {
  const roleLabelById = new Map(roles.map((role) => [role.id, role.name]));
  const defaultUserId =
    users.find((user) => user.id === "voice_experience_user")?.id
    ?? users.find((user) => user.role !== "admin")?.id
    ?? users[0]?.id
    ?? "";
  const loginDisabled = loading || !users.length;
  const voiceScenes = scenes.filter((scene) => scene.id.startsWith("voice_scene_")).slice(0, 20);
  const visibleScenes = voiceScenes.length ? voiceScenes : scenes.filter((scene) => scene.sceneKind === "dialogue").slice(0, 20);

  return (
    <main className="login-shell">
      <section className="hero-select account-select" aria-label="场景选择">
        <header className="hero-select-header">
          <div>
            <h1>选择场景开始对话</h1>
            <p>20 个音色角色，点击卡片进入对应场景。</p>
          </div>
          <form
            className="quick-login"
            onSubmit={(event) => {
              event.preventDefault();
              if (loginDisabled) return;
              const form = new FormData(event.currentTarget);
              void onLogin(String(form.get("userId") || defaultUserId));
            }}
          >
            <label>
              <span>账号</span>
              <select name="userId" defaultValue={defaultUserId} disabled={loginDisabled}>
                {users.map((user) => (
                  <option value={user.id} key={user.id}>
                    {user.name} / {roleLabelById.get(user.role) ?? user.role}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" disabled={loginDisabled} aria-label={loading ? "登录中" : "登录"}>
              <LogIn size={16} />
            </button>
          </form>
        </header>

        <div className="hero-grid" aria-label="音色场景">
          {visibleScenes.map((scene) => {
            const voice = getVoiceOption(scene.config);
            const avatarVideoUrl = voice?.avatarVideoUrl ?? getLocalAvatarVideoUrl("generated/o2-vivi.mp4");
            const avatarPosterUrl = voice?.avatarPosterUrl;
            return (
              <button
                className="hero-card scene-entry-card"
                type="button"
                key={scene.id}
                disabled={loading}
                aria-label={`使用${getSceneCardTitle(scene)}场景`}
                onBlur={(event) => resetCardVideo(event.currentTarget)}
                onClick={() => void onUseScene(scene.id)}
                onFocus={(event) => playCardVideo(event.currentTarget)}
                onMouseEnter={(event) => playCardVideo(event.currentTarget)}
                onMouseLeave={(event) => resetCardVideo(event.currentTarget)}
              >
                <span className="hero-video-frame" aria-hidden="true">
                  <video
                    src={avatarVideoUrl}
                    autoPlay
                    muted
                    loop
                    playsInline
                    preload="auto"
                    poster={avatarPosterUrl}
                  />
                </span>
                <span className="hero-card-copy">
                  <strong>{getSceneCardTitle(scene)}</strong>
                  <small>{scene.config.mode.toUpperCase()}</small>
                  <span>{scene.subtitle}</span>
                  <span className="hero-card-action">
                    <Play size={13} />
                    使用该场景
                  </span>
                </span>
              </button>
            );
          })}
        </div>

        {error ? <div className="connect-error">{error}</div> : null}
      </section>
    </main>
  );
}
