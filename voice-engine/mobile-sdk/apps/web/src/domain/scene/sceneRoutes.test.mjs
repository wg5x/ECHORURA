import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import ts from "typescript";

const sourcePath = new URL("./sceneRoutes.ts", import.meta.url);
const compiled = ts.transpileModule(readFileSync(sourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const compiledPath = join(tmpdir(), `sceneRoutes-${Date.now()}.mjs`);
await import("node:fs/promises").then((fs) => fs.writeFile(compiledPath, compiled, "utf8"));
const {
  buildSceneApplicationPath,
  buildScenePath,
  canStartPlatformSession,
  getSceneListRedirectPath,
  isSceneListRoute,
  parsePlatformRouteOptions,
  resolveSceneRoute,
  shouldShowManualStartButton,
  shouldShowScenePicker,
  shouldShowTextComposer,
} = await import(compiledPath);

const scenes = [
  { id: "podcast_creator_duo", sceneKind: "podcast" },
  { id: "hs6_user_interview", sceneKind: "dialogue" },
];

test("builds sceneKind and sceneId route", () => {
  assert.equal(buildScenePath(scenes[1]), "/scenes/dialogue/hs6_user_interview");
});

test("redirects platform root to scene list", () => {
  assert.equal(getSceneListRedirectPath("/"), "/scenes");
  assert.equal(getSceneListRedirectPath("/scenes"), null);
  assert.equal(isSceneListRoute("/scenes"), true);
  assert.equal(isSceneListRoute("/scenes/"), true);
  assert.equal(isSceneListRoute("/scenes/dialogue/hs6_user_interview"), false);
});

test("builds application route from scene and launch parameters", () => {
  assert.equal(
    buildSceneApplicationPath(scenes[0], {
      consoleTitle: " 播客分析 ",
      recordAudio: true,
      requestId: "req_1",
      saveCallLog: true,
      showTranscript: false,
    }),
    "/scenes/podcast/podcast_creator_duo?embed=1&app=1&recordAudio=1&saveCallLog=1&showTranscript=0&consoleTitle=%E6%92%AD%E5%AE%A2%E5%88%86%E6%9E%90&requestId=req_1",
  );
});

test("resolves route by sceneId and keeps platform query options", () => {
  const match = resolveSceneRoute(
    "/scenes/dialogue/hs6_user_interview",
    "?name=%E5%BC%A0%E4%B8%89&embed=1&app=1&recordAudio=true&showTranscript=false&saveCallLog=0&requestId=request_1",
    scenes,
  );

  assert.equal(match.scene.id, "hs6_user_interview");
  assert.equal(match.sceneKind, "dialogue");
  assert.notEqual(match.scene.id, scenes[0].id);
  assert.deepEqual(match.platformOptions, {
    embed: true,
    app: true,
    recordAudio: true,
    requestId: "request_1",
    saveCallLog: false,
    showTranscript: false,
    trial: false,
  });
});

test("uses scene config as canonical route when URL kind is stale", () => {
  const match = resolveSceneRoute("/scenes/podcast/hs6_user_interview", "", scenes);

  assert.equal(match.sceneKind, "dialogue");
  assert.equal(match.canonicalPath, "/scenes/dialogue/hs6_user_interview");
});

test("hides scene picker in embedded platform routes", () => {
  assert.equal(shouldShowScenePicker({ embed: true }), false);
  assert.equal(shouldShowScenePicker({ embed: false }), true);
});

test("requires requestId before starting an embedded platform session", () => {
  assert.equal(canStartPlatformSession({ embed: true }), false);
  assert.equal(canStartPlatformSession({ embed: true, requestId: "req_1" }), true);
  assert.equal(canStartPlatformSession({ embed: false }), true);
});

test("hides text composer in embedded platform routes", () => {
  assert.equal(shouldShowTextComposer({ embed: true }), false);
  assert.equal(shouldShowTextComposer({ embed: false }), true);
});

test("hides manual start button in embedded platform routes", () => {
  assert.equal(shouldShowManualStartButton({ embed: true }), false);
  assert.equal(shouldShowManualStartButton({ embed: true, app: true }), true);
  assert.equal(shouldShowManualStartButton({ embed: false }), true);
});

test("parses a route-provided console title", () => {
  assert.equal(parsePlatformRouteOptions("?consoleTitle=%E7%BA%A2%E6%97%97%E8%AE%BF%E8%B0%88").consoleTitle, "红旗访谈");
  assert.equal(parsePlatformRouteOptions("?consoleTitle=%20%20").consoleTitle, undefined);
});
