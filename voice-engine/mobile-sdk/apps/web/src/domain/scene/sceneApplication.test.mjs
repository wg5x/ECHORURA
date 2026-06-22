import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import ts from "typescript";

const routesSourcePath = new URL("./sceneRoutes.ts", import.meta.url);
const routesCompiled = ts.transpileModule(readFileSync(routesSourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const routesCompiledPath = join(tmpdir(), `sceneRoutes-${Date.now()}.mjs`);
await import("node:fs/promises").then((fs) => fs.writeFile(routesCompiledPath, routesCompiled, "utf8"));

const kindConfigSourcePath = new URL("./sceneKindConfig.ts", import.meta.url);
const kindConfigCompiled = ts.transpileModule(readFileSync(kindConfigSourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const kindConfigCompiledPath = join(tmpdir(), `sceneKindConfig-${Date.now()}.mjs`);
await import("node:fs/promises").then((fs) => fs.writeFile(kindConfigCompiledPath, kindConfigCompiled, "utf8"));

const sourcePath = new URL("./sceneApplication.ts", import.meta.url);
const compiled = ts.transpileModule(
  readFileSync(sourcePath, "utf8")
    .replace("./sceneKindConfig", kindConfigCompiledPath)
    .replace("./sceneRoutes", routesCompiledPath),
  {
    compilerOptions: {
      module: ts.ModuleKind.ES2020,
      target: ts.ScriptTarget.ES2020,
    },
  },
).outputText;
const compiledPath = join(tmpdir(), `sceneApplication-${Date.now()}.mjs`);
await import("node:fs/promises").then((fs) => fs.writeFile(compiledPath, compiled, "utf8"));
const {
  buildSceneApplicationUrl,
  createSceneApplicationForm,
  getSceneKindLabel,
  SCENE_APPLICATION_CONFIG,
} = await import(compiledPath);

const scene = {
  id: "podcast_creator_duo",
  sceneKind: "podcast",
  title: "语音播客",
};

test("creates application form defaults from configuration", () => {
  assert.deepEqual(
    SCENE_APPLICATION_CONFIG.toggleFields.map((field) => [field.key, field.defaultValue]),
    [
      ["recordAudio", true],
      ["saveCallLog", true],
      ["showTranscript", false],
    ],
  );

  assert.deepEqual(createSceneApplicationForm(scene, "seed.1"), {
    scene,
    consoleTitle: "语音播客",
    recordAudio: true,
    requestId: "app_podcast_creator_duo_seed_1",
    saveCallLog: true,
    showTranscript: false,
  });
});

test("builds application url from configured form values", () => {
  const form = createSceneApplicationForm(scene, "seed.1");
  assert.equal(
    buildSceneApplicationUrl(form),
    "/scenes/podcast/podcast_creator_duo?embed=1&app=1&recordAudio=1&saveCallLog=1&showTranscript=0&consoleTitle=%E8%AF%AD%E9%9F%B3%E6%92%AD%E5%AE%A2&requestId=app_podcast_creator_duo_seed_1",
  );
});

test("reads scene kind labels from application configuration", () => {
  assert.equal(getSceneKindLabel("podcast"), "播客");
  assert.equal(getSceneKindLabel("dialogue"), "聊天");
});
