package com.neuralnexusstudios.nexremote.ui.screens

import android.graphics.BitmapFactory
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.asImageBitmap

@Composable
fun rememberJpegImage(bytes: ByteArray?) = remember(bytes) {
    bytes?.let { BitmapFactory.decodeByteArray(it, 0, it.size)?.asImageBitmap() }
}
