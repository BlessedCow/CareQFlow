package com.blessedcow.careqflow

import android.content.Intent
import android.content.pm.ApplicationInfo
import android.net.Uri
import android.net.http.SslError
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.CookieManager
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.blessedcow.careqflow.config.ServerConfig
import com.google.android.material.appbar.MaterialToolbar

class MainActivity : AppCompatActivity() {
    private lateinit var webView: WebView
    private lateinit var errorView: View
    private lateinit var errorMessage: TextView

    private var configuredServerUrl: String = ServerConfig.DEFAULT_SERVER_URL

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        supportActionBar?.hide()
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        errorView = findViewById(R.id.errorView)
        errorMessage = findViewById(R.id.errorMessage)

        configureToolbar()
        configureWebView()
        configureErrorActions()
        configureBackNavigation()
        configureWindowInsets()

        loadConfiguredServer()
    }

    override fun onResume() {
        super.onResume()

        val storedUrl = ServerConfig.getServerUrl(this)
        if (storedUrl != configuredServerUrl) {
            loadConfiguredServer()
        }
    }

    override fun onDestroy() {
        webView.stopLoading()
        webView.webChromeClient = null
        webView.webViewClient = WebViewClient()
        webView.destroy()
        super.onDestroy()
    }

    private fun configureToolbar() {
        val toolbar = findViewById<MaterialToolbar>(R.id.toolbar)

        toolbar.title = getString(R.string.app_name)
        toolbar.inflateMenu(R.menu.main_menu)
        toolbar.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                R.id.action_reload -> {
                    loadConfiguredServer()
                    true
                }

                R.id.action_server_settings -> {
                    openServerSettings()
                    true
                }

                else -> false
            }
        }
    }

    private fun configureWebView() {
        val isDebuggable = applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0
        WebView.setWebContentsDebuggingEnabled(isDebuggable)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            javaScriptCanOpenWindowsAutomatically = false
            setSupportMultipleWindows(false)
            mediaPlaybackRequiresUserGesture = true

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                safeBrowsingEnabled = true
            }
        }

        CookieManager.getInstance().apply {
            setAcceptCookie(true)
            setAcceptThirdPartyCookies(webView, false)
        }

        webView.webChromeClient = WebChromeClient()

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView,
                request: WebResourceRequest,
            ): Boolean {
                return handleNavigation(request.url.toString())
            }

            @Suppress("DEPRECATION")
            override fun shouldOverrideUrlLoading(
                view: WebView,
                url: String,
            ): Boolean {
                return handleNavigation(url)
            }

            override fun onPageStarted(
                view: WebView,
                url: String,
                favicon: android.graphics.Bitmap?,
            ) {
                showWebView()
            }

            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError,
            ) {
                if (request.isForMainFrame) {
                    showConnectionError(
                        getString(
                            R.string.connection_error_detail,
                            configuredServerUrl,
                        ),
                    )
                }
            }

            override fun onReceivedSslError(
                view: WebView,
                handler: SslErrorHandler,
                error: SslError,
            ) {
                handler.cancel()
                showConnectionError(getString(R.string.tls_error_detail))
            }
        }
    }

    private fun configureErrorActions() {
        findViewById<Button>(R.id.retryButton).setOnClickListener {
            loadConfiguredServer()
        }

        findViewById<Button>(R.id.settingsButton).setOnClickListener {
            openServerSettings()
        }
    }

    private fun configureBackNavigation() {
        onBackPressedDispatcher.addCallback(
            this,
            object : OnBackPressedCallback(true) {
                override fun handleOnBackPressed() {
                    if (webView.canGoBack()) {
                        webView.goBack()
                    } else {
                        finish()
                    }
                }
            },
        )
    }

    private fun configureWindowInsets() {
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(
                systemBars.left,
                systemBars.top,
                systemBars.right,
                systemBars.bottom,
            )
            insets
        }
    }

    private fun loadConfiguredServer() {
        configuredServerUrl = ServerConfig.getServerUrl(this)
        showWebView()
        webView.loadUrl(configuredServerUrl)
    }

    private fun handleNavigation(url: String): Boolean {
        if (ServerConfig.isSameOrigin(url, configuredServerUrl)) {
            return false
        }

        val uri = try {
            Uri.parse(url)
        } catch (_: Exception) {
            return true
        }

        if (uri.scheme.equals("https", ignoreCase = true)) {
            val intent = Intent(Intent.ACTION_VIEW, uri)
            if (intent.resolveActivity(packageManager) != null) {
                startActivity(intent)
            }
        } else {
            Toast.makeText(
                this,
                R.string.blocked_navigation,
                Toast.LENGTH_SHORT,
            ).show()
        }

        return true
    }

    private fun showWebView() {
        errorView.visibility = View.GONE
        webView.visibility = View.VISIBLE
    }

    private fun showConnectionError(message: String) {
        webView.visibility = View.GONE
        errorView.visibility = View.VISIBLE
        errorMessage.text = message
    }

    private fun openServerSettings() {
        startActivity(Intent(this, SettingsActivity::class.java))
    }
}
