import type { CreateSceneInput } from "../app/types";
import type { SceneTemplate } from "../domain/scene/sceneTemplates";
import { AdminManagementPanel } from "./AdminManagementPanel";

type AdminDashboardProps = {
  onCreateScene: (input: CreateSceneInput) => Promise<void>;
  onUpdateScene: (sceneId: string, input: CreateSceneInput) => Promise<void>;
  runtimeScenes: SceneTemplate[];
};

export function AdminDashboard({ onCreateScene, onUpdateScene, runtimeScenes }: AdminDashboardProps) {
  return (
    <section className="admin-page" aria-label="场景后台">
      <div className="admin-page-main">
        <AdminManagementPanel
          onCreateScene={onCreateScene}
          onUpdateScene={onUpdateScene}
          scenes={runtimeScenes}
        />
      </div>
    </section>
  );
}
