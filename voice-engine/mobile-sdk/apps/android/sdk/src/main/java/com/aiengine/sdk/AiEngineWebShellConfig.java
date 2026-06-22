package com.aiengine.sdk;

public final class AiEngineWebShellConfig {
    private final String startUrl;
    private final String updateManifestUrl;
    private final String defaultUpdateUrl;
    private final String bridgeName;
    private final boolean updateCheckEnabled;

    private AiEngineWebShellConfig(Builder builder) {
        this.startUrl = builder.startUrl;
        this.updateManifestUrl = builder.updateManifestUrl;
        this.defaultUpdateUrl = builder.defaultUpdateUrl;
        this.bridgeName = builder.bridgeName;
        this.updateCheckEnabled = builder.updateCheckEnabled;
    }

    public String getStartUrl() {
        return startUrl;
    }

    public String getUpdateManifestUrl() {
        return updateManifestUrl;
    }

    public String getDefaultUpdateUrl() {
        return defaultUpdateUrl;
    }

    public String getBridgeName() {
        return bridgeName;
    }

    public boolean isUpdateCheckEnabled() {
        return updateCheckEnabled;
    }

    public static final class Builder {
        private final String startUrl;
        private String updateManifestUrl = "";
        private String defaultUpdateUrl = "";
        private String bridgeName = "AiEngineAndroid";
        private boolean updateCheckEnabled = false;

        public Builder(String startUrl) {
            this.startUrl = valueOrEmpty(startUrl);
        }

        public Builder setUpdateManifestUrl(String updateManifestUrl) {
            this.updateManifestUrl = valueOrEmpty(updateManifestUrl);
            return this;
        }

        public Builder setDefaultUpdateUrl(String defaultUpdateUrl) {
            this.defaultUpdateUrl = valueOrEmpty(defaultUpdateUrl);
            return this;
        }

        public Builder setBridgeName(String bridgeName) {
            this.bridgeName = valueOrDefault(bridgeName, "AiEngineAndroid");
            return this;
        }

        public Builder setUpdateCheckEnabled(boolean updateCheckEnabled) {
            this.updateCheckEnabled = updateCheckEnabled;
            return this;
        }

        public AiEngineWebShellConfig build() {
            return new AiEngineWebShellConfig(this);
        }

        private static String valueOrDefault(String value, String fallback) {
            String normalized = valueOrEmpty(value);
            return normalized.isEmpty() ? fallback : normalized;
        }
    }

    private static String valueOrEmpty(String value) {
        return value == null ? "" : value.trim();
    }
}
