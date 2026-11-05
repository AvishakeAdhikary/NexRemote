package com.neuralnexusstudios.nex_remote.ui.components

import androidx.compose.foundation.layout.RowScope
import androidx.compose.runtime.Composable
import com.neuralnexusstudios.nex_remote.ui.design.NxTopBar

/** Top bar for screens on the compat bridge; same as [NxTopBar]. */
@Composable
fun AppTopBar(
    title: String,
    onBack: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
) = NxTopBar(title = title, onBack = onBack, actions = actions)
