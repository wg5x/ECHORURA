package com.aiengine.sdk;

public final class AiEngineSdk {
    private AiEngineSdk() {
    }

    public static String getVersionName() {
        return BuildConfig.SDK_VERSION_NAME;
    }
}
