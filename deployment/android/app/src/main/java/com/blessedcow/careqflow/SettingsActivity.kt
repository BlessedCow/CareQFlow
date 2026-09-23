package com.blessedcow.careqflow

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.blessedcow.careqflow.config.ServerConfig

class SettingsActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        supportActionBar?.hide()
        setContentView(R.layout.activity_settings)

        val serverUrl = findViewById<EditText>(R.id.serverUrl)
        val validationMessage = findViewById<TextView>(R.id.validationMessage)

        serverUrl.setText(ServerConfig.getServerUrl(this))

        findViewById<Button>(R.id.saveButton).setOnClickListener {
            try {
                ServerConfig.saveServerUrl(this, serverUrl.text.toString())
                finish()
            } catch (error: IllegalArgumentException) {
                validationMessage.text = error.message ?: getString(R.string.invalid_server_url)
            }
        }

        findViewById<Button>(R.id.cancelButton).setOnClickListener {
            finish()
        }

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.settingsRoot)) { view, insets ->
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
}
