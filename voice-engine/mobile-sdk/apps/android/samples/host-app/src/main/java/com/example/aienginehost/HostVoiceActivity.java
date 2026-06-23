package com.example.aienginehost;

import com.aiengine.sdk.AiEngineWebShellActivity;
import com.aiengine.sdk.AiEngineWebShellConfig;

public class HostVoiceActivity extends AiEngineWebShellActivity {
    @Override
    protected AiEngineWebShellConfig createWebShellConfig() {
        return new AiEngineWebShellConfig.Builder("https://aivoice.token-gpt.top/")
                .setUpdateManifestUrl("https://aivoice.token-gpt.top/android-version.json")
                .setDefaultUpdateUrl("https://www.betaqr.com.cn/bka92l6c")
                .setUpdateCheckEnabled(true)
                .build();
    }
}
