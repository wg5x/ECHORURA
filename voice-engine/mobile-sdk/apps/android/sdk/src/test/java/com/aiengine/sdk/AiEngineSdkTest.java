package com.aiengine.sdk;

import static org.junit.Assert.assertEquals;

import org.junit.Test;

public class AiEngineSdkTest {
    @Test
    public void exposesSdkVersionName() {
        assertEquals("0.2.0", AiEngineSdk.getVersionName());
    }
}
