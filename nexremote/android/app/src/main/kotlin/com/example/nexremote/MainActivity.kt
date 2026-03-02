package com.neuralnexusstudios.nexremote

import android.content.Intent
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.nexremote/settings"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "openSettings" -> {
                        val action = call.argument<String>("action")
                        if (action != null) {
                            try {
                                val intent = Intent(action)
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                startActivity(intent)
                                result.success(true)
                            } catch (e: Exception) {
                                // Fallback: open general settings
                                try {
                                    val fallback = Intent(Settings.ACTION_SETTINGS)
                                    fallback.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                    startActivity(fallback)
                                    result.success(true)
                                } catch (e2: Exception) {
                                    result.error("UNAVAILABLE",
                                        "Could not open settings: ${e2.message}", null)
                                }
                            }
                        } else {
                            result.error("BAD_ARGS", "Missing 'action' argument", null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
