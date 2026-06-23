package com.aiengine.sdk;

public final class AiEngineSelectedFile {
    private final String uri;
    private final String name;
    private final String mimeType;
    private final long size;

    public AiEngineSelectedFile(String uri, String name, String mimeType, long size) {
        this.uri = valueOrEmpty(uri);
        this.name = valueOrEmpty(name);
        this.mimeType = valueOrEmpty(mimeType);
        this.size = Math.max(size, -1L);
    }

    public String getUri() {
        return uri;
    }

    public String getName() {
        return name;
    }

    public String getMimeType() {
        return mimeType;
    }

    public long getSize() {
        return size;
    }

    private static String valueOrEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
