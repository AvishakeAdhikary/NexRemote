package com.neuralnexusstudios.nexremote.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.runtime.Composable
import androidx.compose.runtime.State
import androidx.compose.runtime.produceState
import androidx.compose.ui.graphics.asImageBitmap
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Composable
fun rememberJpegImage(bytes: ByteArray?): State<androidx.compose.ui.graphics.ImageBitmap?> = produceState<androidx.compose.ui.graphics.ImageBitmap?>(initialValue = null, bytes) {
    value = withContext(Dispatchers.Default) {
        bytes?.let { BitmapFactory.decodeByteArray(it, 0, it.size)?.asImageBitmap() }
    }
}
