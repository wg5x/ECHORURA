package com.aiengine.sdk;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.List;

final class AiEngineBridgeEvent {
    private AiEngineBridgeEvent() {
    }

    static String nativeActionResult(String action, boolean success, String message) {
        JSONObject detail = new JSONObject();
        try {
            detail.put("action", valueOrEmpty(action));
            detail.put("success", success);
            detail.put("message", valueOrEmpty(message));
        } catch (Exception ignored) {
            return "";
        }
        return customEvent("ai-engine-android-native-result", detail);
    }

    static String fileSelection(
            String requestId,
            List<AiEngineSelectedFile> files,
            boolean cancelled,
            String error
    ) {
        JSONObject detail = new JSONObject();
        JSONArray fileArray = new JSONArray();

        try {
            if (files != null) {
                for (AiEngineSelectedFile file : files) {
                    JSONObject fileObject = new JSONObject();
                    fileObject.put("uri", file.getUri());
                    fileObject.put("name", file.getName());
                    fileObject.put("mimeType", file.getMimeType());
                    fileObject.put("size", file.getSize());
                    fileArray.put(fileObject);
                }
            }

            detail.put("requestId", valueOrEmpty(requestId));
            detail.put("cancelled", cancelled);
            detail.put("files", fileArray);
            detail.put("error", valueOrEmpty(error));
        } catch (Exception ignored) {
            return "";
        }

        return customEvent("ai-engine-android-file-selection", detail);
    }

    private static String customEvent(String eventName, JSONObject detail) {
        return "window.dispatchEvent(new CustomEvent("
                + JSONObject.quote(eventName)
                + ",{detail:"
                + detail.toString()
                + "}));";
    }

    private static String valueOrEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
