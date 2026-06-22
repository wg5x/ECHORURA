package com.aiengine.sdk;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

public class AiEngineWebShellConfigTest {
    @Test
    public void builderUsesExpectedDefaults() {
        AiEngineWebShellConfig config = new AiEngineWebShellConfig.Builder("https://example.com/")
                .build();

        assertEquals("https://example.com/", config.getStartUrl());
        assertEquals("AiEngineAndroid", config.getBridgeName());
        assertFalse(config.isUpdateCheckEnabled());
        assertEquals("", config.getUpdateManifestUrl());
        assertEquals("", config.getDefaultUpdateUrl());
    }

    @Test
    public void builderStoresExplicitUpdateConfig() {
        AiEngineWebShellConfig config = new AiEngineWebShellConfig.Builder("https://example.com/")
                .setUpdateManifestUrl("https://example.com/android-version.json")
                .setDefaultUpdateUrl("https://example.com/download")
                .setUpdateCheckEnabled(true)
                .setBridgeName("CustomBridge")
                .build();

        assertEquals("https://example.com/android-version.json", config.getUpdateManifestUrl());
        assertEquals("https://example.com/download", config.getDefaultUpdateUrl());
        assertEquals("CustomBridge", config.getBridgeName());
        assertEquals(true, config.isUpdateCheckEnabled());
    }
}
