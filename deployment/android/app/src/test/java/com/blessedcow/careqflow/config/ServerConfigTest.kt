package com.blessedcow.careqflow.config

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ServerConfigTest {
    @Test
    fun normalizeServerUrl_acceptsHttpsHost() {
        assertEquals(
            "https://careqflow.local/",
            ServerConfig.normalizeServerUrl(" https://careqflow.local "),
        )
    }

    @Test
    fun normalizeServerUrl_preservesExplicitPort() {
        assertEquals(
            "https://192.168.1.20:8443/",
            ServerConfig.normalizeServerUrl("https://192.168.1.20:8443/"),
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun normalizeServerUrl_rejectsHttp() {
        ServerConfig.normalizeServerUrl("http://careqflow.local/")
    }

    @Test(expected = IllegalArgumentException::class)
    fun normalizeServerUrl_rejectsCredentials() {
        ServerConfig.normalizeServerUrl("https://user:password@careqflow.local/")
    }

    @Test(expected = IllegalArgumentException::class)
    fun normalizeServerUrl_rejectsPath() {
        ServerConfig.normalizeServerUrl("https://careqflow.local/admin")
    }

    @Test
    fun isSameOrigin_matchesDefaultHttpsPort() {
        assertTrue(
            ServerConfig.isSameOrigin(
                "https://careqflow.local/api/health",
                "https://careqflow.local/",
            ),
        )
    }

    @Test
    fun isSameOrigin_rejectsDifferentHost() {
        assertFalse(
            ServerConfig.isSameOrigin(
                "https://example.com/",
                "https://careqflow.local/",
            ),
        )
    }

    @Test
    fun isSameOrigin_rejectsDifferentPort() {
        assertFalse(
            ServerConfig.isSameOrigin(
                "https://careqflow.local:8443/",
                "https://careqflow.local/",
            ),
        )
    }
}
