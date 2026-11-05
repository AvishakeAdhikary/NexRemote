@file:Suppress("FunctionName")

package com.neuralnexusstudios.nex_remote.ui.design.compat

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.composables.ui.components.ButtonSize
import com.composables.ui.components.ButtonStyle
import com.composeunstyled.LocalContentColor
import com.composeunstyled.ProvideContentColor
import com.composeunstyled.ProvideTextStyle
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxDialog
import com.neuralnexusstudios.nex_remote.ui.design.NxSnackbarHost
import com.neuralnexusstudios.nex_remote.ui.design.NxSnackbarState
import com.neuralnexusstudios.nex_remote.ui.design.NxSpinner
import com.neuralnexusstudios.nex_remote.ui.design.NxTextField
import com.neuralnexusstudios.nex_remote.ui.design.NxType
import com.composables.ui.components.Button as CuiButton
import com.composables.ui.components.Icon as CuiIcon
import com.composables.ui.components.IconButton as CuiIconButton

/*
 * Migration bridge: Material-3-shaped call sites rendered with Composables UI and the NexRemote theme.
 *
 * Screens that have not been redesigned yet import these instead of androidx.compose.material3, so the
 * whole app runs on Composables UI (red/black theme) with Material 3 removed. New and redesigned
 * screens should use the Nx* components in ui/design/Nx.kt directly; delete entries here as their
 * last caller goes away.
 */

// ------------------------------------------------------------------ theme accessors

object MaterialTheme {
    val typography = Typography
    val colorScheme = ColorScheme

    object Typography {
        val headlineSmall: TextStyle get() = NxType.headline
        val titleLarge: TextStyle get() = NxType.headline
        val titleMedium: TextStyle get() = NxType.title
        val titleSmall: TextStyle get() = NxType.titleSmall
        val bodyLarge: TextStyle get() = NxType.body
        val bodyMedium: TextStyle get() = NxType.body
        val bodySmall: TextStyle get() = NxType.bodySmall
        val labelLarge: TextStyle get() = NxType.label.copy(fontWeight = FontWeight.SemiBold)
        val labelMedium: TextStyle get() = NxType.label
        val labelSmall: TextStyle get() = NxType.overline
    }

    object ColorScheme {
        val primary: Color @Composable get() = Nx.primary
        val onPrimary: Color @Composable get() = Nx.onPrimary
        val primaryContainer: Color @Composable get() = Nx.accentSoft
        val secondary: Color @Composable get() = Nx.success
        val tertiary: Color @Composable get() = Nx.warning
        val error: Color @Composable get() = Nx.danger
        val surface: Color @Composable get() = Nx.panel
        val surfaceVariant: Color @Composable get() = Nx.panelRaised
        val surfaceContainerHighest: Color @Composable get() = Nx.panelRaised
        val onSurface: Color @Composable get() = Nx.onPanel
        val onSurfaceVariant: Color @Composable get() = Nx.muted
        val background: Color @Composable get() = Nx.background
        val outline: Color @Composable get() = Nx.border
    }
}

// ------------------------------------------------------------------ text & icons

@Composable
fun Icon(
    imageVector: ImageVector,
    contentDescription: String?,
    modifier: Modifier = Modifier,
    tint: Color = LocalContentColor.current,
) = CuiIcon(imageVector = imageVector, modifier = modifier, contentDescription = contentDescription, tint = tint)

// ------------------------------------------------------------------ surfaces

class CardColors(val containerColor: Color?)

object CardDefaults {
    fun cardColors(containerColor: Color? = null) = CardColors(containerColor)
}

@Composable
fun Card(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    colors: CardColors? = null,
    shape: Shape = RoundedCornerShape(20.dp),
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(
        modifier
            .clip(shape)
            .background(colors?.containerColor ?: Nx.panel)
            .border(1.dp, Nx.border, shape)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier),
    ) {
        ProvideContentColor(Nx.onPanel) { content() }
    }
}

@Composable
fun Surface(
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(0.dp),
    color: Color = Nx.panel,
    border: BorderStroke? = null,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit,
) {
    Box(
        modifier
            .clip(shape)
            .background(color, shape)
            .then(if (border != null) Modifier.border(border, shape) else Modifier)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier),
        propagateMinConstraints = true,
    ) {
        ProvideContentColor(if (color == Color.Transparent) LocalContentColor.current else Nx.onPanel) { content() }
    }
}

// ------------------------------------------------------------------ buttons

@Composable
private fun BridgeButton(
    style: ButtonStyle,
    onClick: () -> Unit,
    modifier: Modifier,
    enabled: Boolean,
    content: @Composable RowScope.() -> Unit,
) {
    CuiButton(onClick = onClick, modifier = modifier, enabled = enabled, style = style, buttonSize = ButtonSize.Default) {
        ProvideTextStyle(NxType.label.copy(fontWeight = FontWeight.SemiBold)) { content() }
    }
}

@Composable
fun Button(onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, content: @Composable RowScope.() -> Unit) =
    BridgeButton(ButtonStyle.Primary, onClick, modifier, enabled, content)

@Composable
fun OutlinedButton(onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, content: @Composable RowScope.() -> Unit) =
    BridgeButton(ButtonStyle.Outlined, onClick, modifier, enabled, content)

@Composable
fun TextButton(onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, content: @Composable RowScope.() -> Unit) =
    BridgeButton(ButtonStyle.Ghost, onClick, modifier, enabled, content)

@Composable
fun IconButton(onClick: () -> Unit, modifier: Modifier = Modifier, enabled: Boolean = true, content: @Composable () -> Unit) =
    CuiIconButton(onClick = onClick, modifier = modifier, enabled = enabled, style = ButtonStyle.Ghost, content = content)

// ------------------------------------------------------------------ chips & segmented

@Composable
fun FilterChip(
    selected: Boolean,
    onClick: () -> Unit,
    label: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    leadingIcon: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier
            .clip(CircleShape)
            .background(if (selected) Nx.selected else Nx.panelRaised)
            .border(1.dp, if (selected) Nx.primary.copy(alpha = 0.6f) else Nx.border, CircleShape)
            .clickable(enabled = enabled, onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        ProvideContentColor(if (selected) Nx.onSelected else Nx.onPanel) {
            ProvideTextStyle(NxType.label) {
                leadingIcon?.invoke()
                label()
            }
        }
    }
}

@Composable
fun AssistChip(
    onClick: () -> Unit,
    label: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    leadingIcon: (@Composable () -> Unit)? = null,
) = FilterChip(selected = false, onClick = onClick, label = label, modifier = modifier, leadingIcon = leadingIcon)

@Composable
fun SingleChoiceSegmentedButtonRow(modifier: Modifier = Modifier, content: @Composable RowScope.() -> Unit) {
    Row(
        modifier
            .fillMaxWidth()
            .clip(CircleShape)
            .background(Nx.panelRaised)
            .border(1.dp, Nx.border, CircleShape)
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
        content = content,
    )
}

object SegmentedButtonDefaults {
    @Suppress("UNUSED_PARAMETER")
    fun itemShape(index: Int, count: Int): Shape = CircleShape
}

@Composable
fun RowScope.SegmentedButton(
    selected: Boolean,
    onClick: () -> Unit,
    shape: Shape = CircleShape,
    modifier: Modifier = Modifier,
    label: @Composable () -> Unit,
) {
    Box(
        modifier
            .weight(1f)
            .clip(shape)
            .background(if (selected) Nx.primary else Color.Transparent)
            .clickable(onClick = onClick)
            .padding(vertical = 9.dp, horizontal = 6.dp),
        contentAlignment = Alignment.Center,
    ) {
        ProvideContentColor(if (selected) Nx.onPrimary else Nx.muted) {
            ProvideTextStyle(NxType.label.copy(fontWeight = FontWeight.SemiBold)) { label() }
        }
    }
}

// ------------------------------------------------------------------ inputs

@Composable
fun OutlinedTextField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    label: (@Composable () -> Unit)? = null,
    labelText: String? = null,
    placeholder: String? = null,
    singleLine: Boolean = false,
    enabled: Boolean = true,
    minLines: Int = 1,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    trailingIcon: (@Composable () -> Unit)? = null,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        if (label != null) {
            Box(Modifier.padding(start = 4.dp)) {
                ProvideContentColor(Nx.muted) { ProvideTextStyle(NxType.label) { label() } }
            }
        }
        NxTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.fillMaxWidth(),
            label = labelText,
            placeholder = placeholder,
            singleLine = singleLine,
            enabled = enabled,
            minLines = minLines,
            keyboardOptions = keyboardOptions,
            trailing = trailingIcon,
        )
    }
}

// ------------------------------------------------------------------ feedback

@Composable
fun AlertDialog(
    onDismissRequest: () -> Unit,
    confirmButton: @Composable () -> Unit,
    modifier: Modifier = Modifier,
    dismissButton: (@Composable () -> Unit)? = null,
    title: (@Composable () -> Unit)? = null,
    text: (@Composable () -> Unit)? = null,
) {
    @Suppress("UNUSED_VARIABLE") val unused = modifier
    com.composables.ui.components.AlertDialog(
        visible = true,
        onDismissRequest = onDismissRequest,
        title = title?.let { t -> { ProvideTextStyle(NxType.title) { t() } } },
        text = { text?.invoke() },
        positiveButton = confirmButton,
        negativeButton = dismissButton,
    )
}

@Composable
fun CircularProgressIndicator(modifier: Modifier = Modifier, size: Dp = 24.dp) = NxSpinner(modifier, size = size)

typealias SnackbarHostState = NxSnackbarState

@Composable
fun SnackbarHost(hostState: SnackbarHostState, modifier: Modifier = Modifier) = NxSnackbarHost(hostState, modifier)

/** Column scaffold: top bar, content, optional bottom bar, snackbar overlay. Content padding is zero. */
@Composable
fun Scaffold(
    modifier: Modifier = Modifier,
    topBar: @Composable () -> Unit = {},
    bottomBar: @Composable () -> Unit = {},
    snackbarHost: @Composable () -> Unit = {},
    content: @Composable (PaddingValues) -> Unit,
) {
    Box(modifier.fillMaxSize().background(Nx.background)) {
        ProvideContentColor(Nx.onBackground) {
            Column(Modifier.fillMaxSize()) {
                topBar()
                Box(Modifier.fillMaxWidth().weight(1f)) { content(PaddingValues(0.dp)) }
                Box(Modifier.windowInsetsPadding(WindowInsets.navigationBars)) { bottomBar() }
            }
            Box(Modifier.align(Alignment.BottomCenter)) { snackbarHost() }
        }
    }
}
