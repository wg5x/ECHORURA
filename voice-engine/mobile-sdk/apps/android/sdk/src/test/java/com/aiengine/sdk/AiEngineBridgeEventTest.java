package com.aiengine.sdk;

import static org.junit.Assert.assertTrue;

import java.util.Arrays;

import org.junit.Test;

public class AiEngineBridgeEventTest {
    @Test
    public void nativeActionResultEscapesPayloadAsJson() {
        String script = AiEngineBridgeEvent.nativeActionResult("shareText", true, "已分享 \"标题\"");

        assertTrue(script.contains("ai-engine-android-native-result"));
        assertTrue(script.contains("\"action\":\"shareText\""));
        assertTrue(script.contains("\"success\":true"));
        assertTrue(script.contains("已分享 \\\"标题\\\""));
    }

    @Test
    public void fileSelectionIncludesRequestAndFileMetadata() {
        String script = AiEngineBridgeEvent.fileSelection(
                "audio-request-1",
                Arrays.asList(new AiEngineSelectedFile(
                        "content://media/audio/1",
                        "recording.wav",
                        "audio/wav",
                        4096L
                )),
                false,
                ""
        );

        assertTrue(script.contains("ai-engine-android-file-selection"));
        assertTrue(script.contains("\"requestId\":\"audio-request-1\""));
        assertTrue(script.contains("\"cancelled\":false"));
        assertTrue(script.contains("\"uri\":\"content://media/audio/1\""));
        assertTrue(script.contains("\"name\":\"recording.wav\""));
        assertTrue(script.contains("\"mimeType\":\"audio/wav\""));
        assertTrue(script.contains("\"size\":4096"));
    }
}
