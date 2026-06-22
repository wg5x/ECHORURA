package com.aiengine.ai;

import com.aiengine.sdk.AiEngineWebShellActivity;
import com.aiengine.sdk.AiEngineWebShellConfig;

public class MainActivity extends AiEngineWebShellActivity {
    @Override
    protected AiEngineWebShellConfig createWebShellConfig() {
        return new AiEngineWebShellConfig.Builder("https://aivoice.token-gpt.top/")
                .setUpdateManifestUrl("https://aivoice.token-gpt.top/android-version.json")
                .setDefaultUpdateUrl("https://www.betaqr.com.cn/bka92l6c")
                .setUpdateCheckEnabled(true)
                .build();
    }
}
