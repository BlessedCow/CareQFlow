package com.blessedcow.careqflow.config

import android.content.Context
import java.net.URI

object ServerConfig {
    const val DEFAULT_SERVER_URL = "https://careqflow.local/"

    private const val PREFERENCES_NAME = "careqflow_android"
    private const val SERVER_URL_KEY = "server_url"

    fun getServerUrl(context: Context): String {
        val preferences = context.getSharedPreferences(
            PREFERENCES_NAME,
            Context.MODE_PRIVATE,
        )

        return preferences.getString(SERVER_URL_KEY, DEFAULT_SERVER_URL)
            ?: DEFAULT_SERVER_URL
    }

    fun saveServerUrl(context: Context, value: String): String {
        val normalized = normalizeServerUrl(value)

        context.getSharedPreferences(
            PREFERENCES_NAME,
            Context.MODE_PRIVATE,
        ).edit()
            .putString(SERVER_URL_KEY, normalized)
            .apply()

        return normalized
    }

    fun normalizeServerUrl(value: String): String {
        val trimmed = value.trim()

        require(trimmed.isNotEmpty()) {
            "Enter the CareQFlow server URL."
        }

        val uri = try {
            URI(trimmed)
        } catch (_: Exception) {
            throw IllegalArgumentException("Enter a valid HTTPS URL.")
        }

        require(uri.scheme.equals("https", ignoreCase = true)) {
            "CareQFlow requires HTTPS."
        }

        require(!uri.host.isNullOrBlank()) {
            "Enter a valid CareQFlow host name or IP address."
        }

        require(uri.userInfo == null) {
            "Credentials cannot be included in the server URL."
        }

        require(uri.query == null && uri.fragment == null) {
            "The server URL cannot contain a query or fragment."
        }

        require(uri.path.isNullOrEmpty() || uri.path == "/") {
            "Use the CareQFlow server root URL."
        }

        val port = if (uri.port == -1) "" else ":${uri.port}"
        return "https://${uri.host}$port/"
    }

    fun isSameOrigin(candidateUrl: String, serverUrl: String): Boolean {
        return try {
            val candidate = URI(candidateUrl)
            val server = URI(serverUrl)

            candidate.scheme.equals(server.scheme, ignoreCase = true) &&
                candidate.host.equals(server.host, ignoreCase = true) &&
                effectivePort(candidate) == effectivePort(server)
        } catch (_: Exception) {
            false
        }
    }

    private fun effectivePort(uri: URI): Int {
        if (uri.port != -1) {
            return uri.port
        }

        return when (uri.scheme.lowercase()) {
            "https" -> 443
            "http" -> 80
            else -> -1
        }
    }
}
