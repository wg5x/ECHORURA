import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import ts from "typescript";

const sourcePath = new URL("./appRoutes.ts", import.meta.url);
const configSourcePath = new URL("./appConfig.ts", import.meta.url);
const configCompiled = ts.transpileModule(readFileSync(configSourcePath, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const configCompiledPath = join(tmpdir(), `interview-link-appConfig-${Date.now()}.mjs`);
await writeFile(configCompiledPath, configCompiled, "utf8");
const compiled = ts.transpileModule(readFileSync(sourcePath, "utf8").replace("./appConfig", configCompiledPath), {
  compilerOptions: {
    module: ts.ModuleKind.ES2020,
    target: ts.ScriptTarget.ES2020,
  },
}).outputText;
const compiledPath = join(tmpdir(), `interview-link-appRoutes-${Date.now()}.mjs`);
await writeFile(compiledPath, compiled, "utf8");
const { buildPlatformInterviewUrl, resolveAppRoute, shouldMountPlatformFrame } = await import(compiledPath);
const { APP_CONFIG } = await import(configCompiledPath);

test("uses the public interview route by default", () => {
  assert.equal(resolveAppRoute("/"), "interview");
  assert.equal(resolveAppRoute("/anything-else"), "interview");
});

test("uses a separate admin route for the request list", () => {
  assert.equal(resolveAppRoute("/admin"), "admin");
  assert.equal(resolveAppRoute("/admin/"), "admin");
});

test("uses the admin route when deployed below a base path", () => {
  assert.equal(resolveAppRoute("/interview-link/admin", "/interview-link/"), "admin");
  assert.equal(resolveAppRoute("/interview-link/admin/", "/interview-link/"), "admin");
});

test("builds the fixed platform scene URL with platform params and requestId", () => {
  const url = buildPlatformInterviewUrl("http://127.0.0.1:5176/", "req_1");
  const expectedParams = new URLSearchParams({
    embed: APP_CONFIG.platformOptions.embed ? "1" : "0",
    recordAudio: APP_CONFIG.platformOptions.recordAudio ? "1" : "0",
    saveCallLog: APP_CONFIG.platformOptions.saveCallLog ? "1" : "0",
    showTranscript: APP_CONFIG.platformOptions.showTranscript ? "1" : "0",
    consoleTitle: APP_CONFIG.platformOptions.consoleTitle,
    requestId: "req_1",
  });

  assert.equal(
    url,
    `http://127.0.0.1:5176/scenes/${APP_CONFIG.sceneKind}/${APP_CONFIG.sceneId}?${expectedParams.toString()}`,
  );
});

test("mounts the platform frame only after a business request exists", () => {
  assert.equal(shouldMountPlatformFrame(null), false);
  assert.equal(shouldMountPlatformFrame(undefined), false);
  assert.equal(shouldMountPlatformFrame(""), false);
  assert.equal(shouldMountPlatformFrame("req_1"), true);
});
