import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const outputFile = "/tmp/ai-engine-call-session-check.mjs";
const bargeInOutputFile = "/tmp/ai-engine-barge-in-check.mjs";
const webPackageUrl = new URL("../apps/web/package.json", import.meta.url);
const webDir = fileURLToPath(new URL("../apps/web", import.meta.url));
const requireFromWeb = createRequire(webPackageUrl);
const { build } = requireFromWeb("esbuild");

await build({
  entryPoints: ["src/features/call/callSession.ts"],
  absWorkingDir: webDir,
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: outputFile,
  external: ["react"],
  alias: {
    "@ai-engine/shared": "./src/shared/index.ts",
  },
  logLevel: "silent",
});

const { appendDisplayEvent, appendTranscriptEvent } = await import(pathToFileURL(outputFile).href);

await build({
  entryPoints: ["src/lib/bargeIn.ts"],
  absWorkingDir: webDir,
  bundle: true,
  platform: "node",
  format: "esm",
  outfile: bargeInOutputFile,
  logLevel: "silent",
});

const {
  createBargeInSnapshot,
  observeBargeInAudio,
  shouldConfirmBargeInFromAsr,
} = await import(pathToFileURL(bargeInOutputFile).href);

const first = {
  id: "assistant-1",
  type: "assistant",
  text: "ChatResponse: 第一段",
  at: "20:00:00",
  outputId: "output-1",
};
const sameOutput = {
  id: "assistant-2",
  type: "assistant",
  text: "ChatResponse: 第一段继续",
  at: "20:00:01",
  outputId: "output-1",
};
const differentOutput = {
  id: "assistant-3",
  type: "assistant",
  text: "ChatResponse: 第二段",
  at: "20:00:02",
  outputId: "output-2",
};

const mergedDisplay = appendDisplayEvent([first], sameOutput);
assert.equal(mergedDisplay.length, 1);
assert.equal(mergedDisplay[0].outputId, "output-1");
assert.match(mergedDisplay[0].text, /第一段继续/);

const splitDisplay = appendDisplayEvent([first], differentOutput);
assert.equal(splitDisplay.length, 2);
assert.equal(splitDisplay[0].outputId, "output-2");
assert.equal(splitDisplay[1].outputId, "output-1");

const mergedTranscript = appendTranscriptEvent([first], sameOutput);
assert.equal(mergedTranscript.length, 1);
assert.equal(mergedTranscript[0].outputId, "output-1");

const splitTranscript = appendTranscriptEvent([first], differentOutput);
assert.equal(splitTranscript.length, 2);
assert.equal(splitTranscript[0].outputId, "output-1");
assert.equal(splitTranscript[1].outputId, "output-2");

const userAsrBetweenSameOutput = {
  id: "asr-1",
  type: "asr",
  text: "ASRResponse: 嗯",
  at: "20:00:02",
};

const interruptedDisplay = [first, userAsrBetweenSameOutput, sameOutput].reduce(
  (events, event) => appendDisplayEvent(events, event),
  [],
);
assert.equal(interruptedDisplay.filter((event) => event.type === "assistant").length, 1);
assert.equal(interruptedDisplay.length, 2);
assert.equal(interruptedDisplay[0].type, "asr");
assert.equal(interruptedDisplay[1].outputId, "output-1");
assert.match(interruptedDisplay[1].text, /第一段继续/);

const interruptedTranscript = [first, userAsrBetweenSameOutput, sameOutput].reduce(
  (events, event) => appendTranscriptEvent(events, event),
  [],
);
assert.equal(interruptedTranscript.filter((event) => event.type === "assistant").length, 1);
assert.equal(interruptedTranscript.length, 2);
assert.equal(interruptedTranscript[0].outputId, "output-1");
assert.equal(interruptedTranscript[1].type, "asr");
assert.match(interruptedTranscript[0].text, /第一段继续/);

const duplicateOutput = {
  id: "assistant-4",
  type: "assistant",
  text: "ChatResponse: 第一段",
  at: "20:00:03",
  outputId: "output-9",
};

const dedupDisplay = appendDisplayEvent([first], duplicateOutput);
assert.equal(dedupDisplay.length, 1);
assert.match(dedupDisplay[0].text, /第一段/);

const dedupTranscript = appendTranscriptEvent([first], duplicateOutput);
assert.equal(dedupTranscript.length, 1);

const repeatedWithParticle = {
  id: "assistant-5",
  type: "assistant",
  text: "ChatResponse: 不好意思，我们这次访谈的样本城市主要是济南、成都、郑州、杭州、深圳、长沙及周边，北京暂时不在样本范围内，这次可能没法继续访问了。感谢您的理解啊。",
  at: "20:00:04",
  outputId: "output-10",
};
const repeatedWithDifferentParticle = {
  id: "assistant-6",
  type: "assistant",
  text: "ChatResponse: 不好意思，我们这次访谈的样本城市主要是济南、成都、郑州、杭州、深圳、长沙及周边，北京暂时不在样本范围内，这次可能没法继续访问了。谢谢您的理解呀。",
  at: "20:00:05",
  outputId: "output-11",
};

const particleDisplay = appendDisplayEvent([repeatedWithParticle], repeatedWithDifferentParticle);
assert.equal(particleDisplay.length, 1);
assert.match(particleDisplay[0].text, /(感谢|谢谢)您的理解/);

const particleTranscript = appendTranscriptEvent([repeatedWithParticle], repeatedWithDifferentParticle);
assert.equal(particleTranscript.length, 1);

const repeatedQuestion = {
  id: "assistant-7",
  type: "assistant",
  text: "ChatResponse: 好的，那确定是杭州哈。接下来想问一下，您有驾照吗？目前是正常可用状态吧?",
  at: "20:00:06",
  outputId: "output-12",
};
const repeatedQuestionVariant = {
  id: "assistant-8",
  type: "assistant",
  text: "ChatResponse: 好的，那确定是杭州哈。接下来想问一下，您有驾照吗？目前是正常可用的状态吧？",
  at: "20:00:07",
  outputId: "output-13",
};

const questionDisplay = appendDisplayEvent([repeatedQuestion], repeatedQuestionVariant);
assert.equal(questionDisplay.length, 1);

const questionTranscript = appendTranscriptEvent([repeatedQuestion], repeatedQuestionVariant);
assert.equal(questionTranscript.length, 1);

const sampleCityMismatchFirst = {
  id: "assistant-8a",
  type: "assistant",
  text: "ChatResponse: 抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要可能没法继续访谈了，谢谢您的理解。",
  at: "20:00:07",
  outputId: "output-13a",
};
const sampleCityMismatchCorrected = {
  id: "assistant-8b",
  type: "assistant",
  text: "ChatResponse: 抱歉，这次我们的访谈样本主要针对济南、成都、郑州、杭州、深圳、长沙及周边的用户，北京的样本暂时不需要，这次可能没法继续访谈了，谢谢您的理解。",
  at: "20:00:08",
  outputId: "output-13b",
};

const sampleCityDisplay = appendDisplayEvent([sampleCityMismatchFirst], sampleCityMismatchCorrected);
assert.equal(sampleCityDisplay.length, 1);
assert.equal(sampleCityDisplay[0].text, sampleCityMismatchCorrected.text);

const sampleCityTranscript = appendTranscriptEvent([sampleCityMismatchFirst], sampleCityMismatchCorrected);
assert.equal(sampleCityTranscript.length, 1);
assert.equal(sampleCityTranscript[0].text, sampleCityMismatchCorrected.text);

const shortCorrectionFirst = {
  id: "assistant-8c",
  type: "assistant",
  text: "ChatResponse: 那当然，我说话可是很清晰的，你可要好听哦。",
  at: "20:00:09",
  outputId: "output-13c",
};
const shortCorrectionNext = {
  id: "assistant-8d",
  type: "assistant",
  text: "ChatResponse: 那当然，我说话可是很清晰的，你可要好好听哦。",
  at: "20:00:10",
  outputId: "output-13d",
};

const shortCorrectionDisplay = appendDisplayEvent([shortCorrectionFirst], shortCorrectionNext);
assert.equal(shortCorrectionDisplay.length, 1);
assert.equal(shortCorrectionDisplay[0].text, shortCorrectionNext.text);

const shortCorrectionTranscript = appendTranscriptEvent([shortCorrectionFirst], shortCorrectionNext);
assert.equal(shortCorrectionTranscript.length, 1);
assert.equal(shortCorrectionTranscript[0].text, shortCorrectionNext.text);

const shortDifferentDisplay = appendDisplayEvent(
  [{
    id: "assistant-8e",
    type: "assistant",
    text: "ChatResponse: 好的，那我们继续。",
    at: "20:00:11",
    outputId: "output-13e",
  }],
  {
    id: "assistant-8f",
    type: "assistant",
    text: "ChatResponse: 好的，那我们结束。",
    at: "20:00:12",
    outputId: "output-13f",
  },
);
assert.equal(shortDifferentDisplay.length, 2);

const forcedDuplicateDisplay = appendDisplayEvent([repeatedQuestion], repeatedQuestionVariant, { forceNewTurn: true });
assert.equal(forcedDuplicateDisplay.length, 1);

const forcedDuplicateTranscript = appendTranscriptEvent([repeatedQuestion], repeatedQuestionVariant, { forceNewTurn: true });
assert.equal(forcedDuplicateTranscript.length, 1);

const chatResponseWithUnspokenCity = {
  id: "assistant-9",
  type: "assistant",
  text: "ChatResponse: 好的，那就是杭州。您最近半年有参加过其他汽车相关的市场调查吗？",
  at: "20:00:08",
  outputId: "output-14",
};
const actualTtsWithoutCity = {
  id: "assistant-10",
  type: "assistant",
  text: "ChatResponse: 好的，那就是。您最近半年有参加过其他汽车相关的市场调查吗？",
  at: "20:00:09",
  outputId: "output-14",
};

const correctedDisplay = appendDisplayEvent([chatResponseWithUnspokenCity], actualTtsWithoutCity);
assert.equal(correctedDisplay.length, 1);
assert.equal(correctedDisplay[0].text, actualTtsWithoutCity.text);

const correctedTranscript = appendTranscriptEvent([chatResponseWithUnspokenCity], actualTtsWithoutCity);
assert.equal(correctedTranscript.length, 1);
assert.equal(correctedTranscript[0].text, actualTtsWithoutCity.text);

assert.equal(
  shouldConfirmBargeInFromAsr("ASRResponse: 成都", "请问您目前主要在哪个城市生活呢？", 1000, 1200),
  true,
);
assert.equal(
  shouldConfirmBargeInFromAsr("ASRResponse: 嗯", "请问您目前主要在哪个城市生活呢？", 1000, 1200),
  false,
);
assert.equal(
  shouldConfirmBargeInFromAsr("ASRResponse: 好的", "请问您目前主要在哪个城市生活呢？", 1000, 1200),
  false,
);

const speechFrame = new Float32Array(2048).fill(0.09);
const firstCandidateFrame = observeBargeInAudio(speechFrame, true, createBargeInSnapshot(), 1000);
const confirmedCandidateFrame = observeBargeInAudio(speechFrame, true, firstCandidateFrame, 1030);
assert.equal(firstCandidateFrame.state, "assistant_speaking");
assert.equal(confirmedCandidateFrame.state, "user_speech_candidate");
assert.equal(confirmedCandidateFrame.recentSpeechCandidateAt, 1030);

const impulseNoiseFrame = new Float32Array(2048);
impulseNoiseFrame[10] = 0.2;
const firstNoiseFrame = observeBargeInAudio(impulseNoiseFrame, true, createBargeInSnapshot(), 2000);
const secondNoiseFrame = observeBargeInAudio(impulseNoiseFrame, true, firstNoiseFrame, 2030);
assert.equal(firstNoiseFrame.state, "assistant_speaking");
assert.equal(secondNoiseFrame.state, "assistant_speaking");
assert.equal(secondNoiseFrame.recentSpeechCandidateAt, null);

function makeTransientNoiseFrame(amplitude) {
  const frame = new Float32Array(2048);
  for (let index = 0; index < 96; index += 1) {
    frame[index] = amplitude * (1 - index / 96);
  }
  return frame;
}

const transientNoiseFrames = [0.9, 0.45, 0.2, 0.08].reduce(
  (snapshot, amplitude, index) => observeBargeInAudio(makeTransientNoiseFrame(amplitude), true, snapshot, 3000 + index * 30),
  createBargeInSnapshot(),
);
assert.equal(transientNoiseFrames.state, "assistant_speaking");
assert.equal(transientNoiseFrames.recentSpeechCandidateAt, null);

console.log("callSession outputId merge check passed");
