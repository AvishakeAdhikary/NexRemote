package com.neuralnexusstudios.nex_remote.ui.design

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.input.TextFieldLineLimits
import androidx.compose.foundation.text.input.rememberTextFieldState
import androidx.compose.foundation.text.input.setTextAndPlaceCursorAtEnd
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowBack
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.composables.ui.components.AlertDialog
import com.composables.ui.components.Button
import com.composables.ui.components.ButtonSize
import com.composables.ui.components.ButtonStyle
import com.composables.ui.components.Icon
import com.composables.ui.components.IconButton
import com.composables.ui.components.Switch
import com.composables.ui.components.Text
import com.composables.ui.components.TextField
import com.composables.ui.theme.backgroundColor
import com.composables.ui.theme.borderColor
import com.composables.ui.theme.colors
import com.composables.ui.theme.destructiveColor
import com.composables.ui.theme.mutedColor
import com.composables.ui.theme.onBackgroundColor
import com.composables.ui.theme.onPanelColor
import com.composables.ui.theme.onPrimaryColor
import com.composables.ui.theme.onSelectedControlColor
import com.composables.ui.theme.panelColor
import com.composables.ui.theme.primaryColor
import com.composables.ui.theme.selectedControlColor
import com.composeunstyled.ProvideContentColor
import com.composeunstyled.theme.Theme
import com.neuralnexusstudios.nex_remote.ui.theme.accentSoftColor
import com.neuralnexusstudios.nex_remote.ui.theme.panelRaisedColor
import com.neuralnexusstudios.nex_remote.ui.theme.successColor
import com.neuralnexusstudios.nex_remote.ui.theme.warningColor
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.filter

/** Theme colour shortcuts for NexRemote screens. */
object Nx {
    val background: Color @Composable get() = Theme[colors][backgroundColor]
    val onBackground: Color @Composable get() = Theme[colors][onBackgroundColor]
    val panel: Color @Composable get() = Theme[colors][panelColor]
    val panelRaised: Color @Composable get() = Theme[colors][panelRaisedColor]
    val onPanel: Color @Composable get() = Theme[colors][onPanelColor]
    val muted: Color @Composable get() = Theme[colors][mutedColor]
    val primary: Color @Composable get() = Theme[colors][primaryColor]
    val onPrimary: Color @Composable get() = Theme[colors][onPrimaryColor]
    val accentSoft: Color @Composable get() = Theme[colors][accentSoftColor]
    val selected: Color @Composable get() = Theme[colors][selectedControlColor]
    val onSelected: Color @Composable get() = Theme[colors][onSelectedControlColor]
    val danger: Color @Composable get() = Theme[colors][destructiveColor]
    val success: Color @Composable get() = Theme[colors][successColor]
    val warning: Color @Composable get() = Theme[colors][warningColor]
    val border: Color @Composable get() = Theme[colors][borderColor]
}

/** Type scale. */
object NxType {
    val display = TextStyle(fontSize = 30.sp, lineHeight = 36.sp, fontWeight = FontWeight.Bold, letterSpacing = (-0.5).sp)
    val headline = TextStyle(fontSize = 22.sp, lineHeight = 28.sp, fontWeight = FontWeight.Bold)
    val title = TextStyle(fontSize = 17.sp, lineHeight = 23.sp, fontWeight = FontWeight.SemiBold)
    val titleSmall = TextStyle(fontSize = 15.sp, lineHeight = 20.sp, fontWeight = FontWeight.SemiBold)
    val body = TextStyle(fontSize = 15.sp, lineHeight = 21.sp)
    val bodySmall = TextStyle(fontSize = 13.sp, lineHeight = 18.sp)
    val label = TextStyle(fontSize = 13.sp, lineHeight = 16.sp, fontWeight = FontWeight.Medium)
    val overline = TextStyle(fontSize = 11.sp, lineHeight = 14.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.2.sp)
    val mono = TextStyle(fontSize = 13.sp, lineHeight = 18.sp, fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace)
}

// ---------------------------------------------------------------- scaffold

/**
 * Screen frame: black background, Composables UI toolbar with an optional back arrow, content below.
 * [content] receives padding that already includes the navigation-bar inset.
 */
@Composable
fun NxScaffold(
    title: String,
    onBack: (() -> Unit)? = null,
    snackbar: NxSnackbarState? = null,
    actions: @Composable RowScope.() -> Unit = {},
    titleContent: (@Composable RowScope.() -> Unit)? = null,
    content: @Composable BoxScope.(PaddingValues) -> Unit,
) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Nx.background),
    ) {
        ProvideContentColor(Nx.onBackground) {
            Column(Modifier.fillMaxSize()) {
                NxTopBar(title = title, onBack = onBack, actions = actions, titleContent = titleContent)
                Box(Modifier.fillMaxWidth().weight(1f)) {
                    content(PaddingValues(bottom = 0.dp))
                }
                Box(Modifier.windowInsetsPadding(WindowInsets.navigationBars))
            }
            snackbar?.let { NxSnackbarHost(it, Modifier.align(Alignment.BottomCenter)) }
        }
    }
}

/**
 * Top bar: back arrow, title (weighted, ellipsized so it never runs under the actions), actions.
 * Pads for the status bar itself.
 */
@Composable
fun NxTopBar(
    title: String,
    onBack: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
    titleContent: (@Composable RowScope.() -> Unit)? = null,
) {
    Row(
        Modifier
            .fillMaxWidth()
            .windowInsetsPadding(WindowInsets.statusBars)
            .height(64.dp)
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        if (onBack != null) {
            NxIconButton(Icons.AutoMirrored.Outlined.ArrowBack, contentDescription = "Back", onClick = onBack)
        } else {
            Box(Modifier.size(8.dp))
        }
        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            if (titleContent != null) {
                titleContent()
            } else {
                Text(title, style = NxType.headline, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
        }
        actions()
    }
}

// ---------------------------------------------------------------- surfaces

enum class NxTone { Default, Raised, Accent, Danger, Success, Warning }

@Composable
private fun toneColors(tone: NxTone): Pair<Color, Color> = when (tone) {
    NxTone.Default -> Nx.panel to Nx.border
    NxTone.Raised -> Nx.panelRaised to Nx.border
    NxTone.Accent -> Nx.accentSoft to Nx.primary.copy(alpha = 0.35f)
    NxTone.Danger -> Nx.danger.copy(alpha = 0.10f) to Nx.danger.copy(alpha = 0.35f)
    NxTone.Success -> Nx.success.copy(alpha = 0.10f) to Nx.success.copy(alpha = 0.30f)
    NxTone.Warning -> Nx.warning.copy(alpha = 0.10f) to Nx.warning.copy(alpha = 0.35f)
}

/** Rounded panel with a hairline border. Clickable when [onClick] is set. */
@Composable
fun NxCard(
    modifier: Modifier = Modifier,
    tone: NxTone = NxTone.Default,
    onClick: (() -> Unit)? = null,
    contentPadding: PaddingValues = PaddingValues(18.dp),
    shape: RoundedCornerShape = RoundedCornerShape(22.dp),
    content: @Composable ColumnScope.() -> Unit,
) {
    val (bg, line) = toneColors(tone)
    Column(
        modifier
            .clip(shape)
            .background(bg)
            .border(BorderStroke(1.dp, line), shape)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(contentPadding),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        ProvideContentColor(Nx.onPanel) { content() }
    }
}

/** Square-ish icon tile, red-tinted when [active]. */
@Composable
fun NxIconWell(
    icon: ImageVector,
    modifier: Modifier = Modifier,
    active: Boolean = true,
    size: Dp = 44.dp,
    tint: Color? = null,
) {
    Box(
        modifier
            .size(size)
            .clip(RoundedCornerShape(size * 0.32f))
            .background(if (active) Nx.accentSoft else Nx.panelRaised),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = null, tint = tint ?: if (active) Nx.primary else Nx.muted, modifier = Modifier.size(size * 0.5f))
    }
}

@Composable
fun NxSectionLabel(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), style = NxType.overline, color = Nx.muted, modifier = modifier.padding(start = 4.dp, top = 6.dp))
}

/** Dot + label status pill. */
@Composable
fun NxStatusPill(text: String, color: Color, modifier: Modifier = Modifier) {
    Row(
        modifier
            .clip(CircleShape)
            .background(color.copy(alpha = 0.12f))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(Modifier.size(7.dp).clip(CircleShape).background(color))
        Text(text, style = NxType.label, color = color)
    }
}

/** Title/subtitle row with optional leading icon and trailing slot. */
@Composable
fun NxListRow(
    title: String,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    icon: ImageVector? = null,
    iconActive: Boolean = true,
    onClick: (() -> Unit)? = null,
    trailing: (@Composable () -> Unit)? = null,
) {
    Row(
        modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier)
            .padding(vertical = 10.dp, horizontal = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        icon?.let { NxIconWell(it, active = iconActive, size = 40.dp) }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = NxType.titleSmall)
            subtitle?.let { Text(it, style = NxType.bodySmall, color = Nx.muted) }
        }
        trailing?.invoke()
    }
}

@Composable
fun NxSwitchRow(
    title: String,
    subtitle: String?,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
) {
    NxListRow(
        title = title,
        subtitle = subtitle,
        icon = icon,
        modifier = modifier.alpha(if (enabled) 1f else 0.5f),
        onClick = if (enabled) ({ onCheckedChange(!checked) }) else null,
        trailing = { Switch(checked = checked, onCheckedChange = onCheckedChange, enabled = enabled, accessibilityLabel = title) },
    )
}

// ---------------------------------------------------------------- buttons

enum class NxButtonKind { Primary, Secondary, Outlined, Ghost, Danger }

@Composable
fun NxButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    kind: NxButtonKind = NxButtonKind.Primary,
    icon: ImageVector? = null,
    enabled: Boolean = true,
    small: Boolean = false,
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        style = when (kind) {
            NxButtonKind.Primary -> ButtonStyle.Primary
            NxButtonKind.Secondary -> ButtonStyle.Secondary
            NxButtonKind.Outlined -> ButtonStyle.Outlined
            NxButtonKind.Ghost -> ButtonStyle.Ghost
            NxButtonKind.Danger -> ButtonStyle.Destructive
        },
        buttonSize = if (small) ButtonSize.Small else ButtonSize.Default,
    ) {
        icon?.let { Icon(it, contentDescription = null, modifier = Modifier.size(18.dp)) }
        Text(text, style = NxType.label.copy(fontSize = if (small) 13.sp else 15.sp, fontWeight = FontWeight.SemiBold), maxLines = 1)
    }
}

@Composable
fun NxIconButton(
    icon: ImageVector,
    contentDescription: String?,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    tint: Color? = null,
    filled: Boolean = false,
) {
    IconButton(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        style = if (filled) ButtonStyle.Secondary else ButtonStyle.Ghost,
    ) {
        Icon(icon, contentDescription = contentDescription, tint = tint ?: com.composeunstyled.LocalContentColor.current, modifier = Modifier.size(22.dp))
    }
}

/** Selectable pill (filter/assist chip replacement). */
@Composable
fun NxChip(
    label: String,
    selected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    icon: ImageVector? = null,
    enabled: Boolean = true,
) {
    val shape = CircleShape
    Row(
        modifier
            .clip(shape)
            .background(if (selected) Nx.selected else Nx.panelRaised)
            .border(1.dp, if (selected) Nx.primary.copy(alpha = 0.6f) else Nx.border, shape)
            .clickable(enabled = enabled, onClick = onClick)
            .alpha(if (enabled) 1f else 0.5f)
            .padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        val color = if (selected) Nx.onSelected else Nx.onPanel
        icon?.let { Icon(it, contentDescription = null, tint = color, modifier = Modifier.size(16.dp)) }
        Text(label, style = NxType.label, color = color, maxLines = 1)
    }
}

/** Segmented control (tabs / segmented buttons replacement). */
@Composable
fun NxSegmented(
    options: List<String>,
    selectedIndex: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier
            .clip(CircleShape)
            .background(Nx.panelRaised)
            .border(1.dp, Nx.border, CircleShape)
            .padding(4.dp),
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        options.forEachIndexed { index, option ->
            val selected = index == selectedIndex
            Box(
                Modifier
                    .weight(1f)
                    .clip(CircleShape)
                    .background(if (selected) Nx.primary else Color.Transparent)
                    .clickable { onSelect(index) }
                    .padding(vertical = 9.dp, horizontal = 8.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    option,
                    style = NxType.label.copy(fontWeight = FontWeight.SemiBold),
                    color = if (selected) Nx.onPrimary else Nx.muted,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}

// ---------------------------------------------------------------- inputs

/** String-based text field over Composables UI's state-based TextField, with a label above it. */
@Composable
fun NxTextField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    label: String? = null,
    placeholder: String? = null,
    singleLine: Boolean = true,
    enabled: Boolean = true,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    leadingIcon: ImageVector? = null,
    trailing: (@Composable () -> Unit)? = null,
    minLines: Int = 1,
) {
    val state = rememberTextFieldState(value)
    val latest by rememberUpdatedState(onValueChange)
    // Compare against the current value, not the one captured when the field first composed;
    // otherwise typing the text back to its original value was silently dropped.
    val currentValue by rememberUpdatedState(value)
    LaunchedEffect(value) {
        if (state.text.toString() != value) state.setTextAndPlaceCursorAtEnd(value)
    }
    LaunchedEffect(state) {
        snapshotFlow { state.text.toString() }
            .filter { it != currentValue }
            .collect { latest(it) }
    }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        label?.let { Text(it, style = NxType.label, color = Nx.muted, modifier = Modifier.padding(start = 4.dp)) }
        TextField(
            state = state,
            modifier = Modifier.fillMaxWidth(),
            enabled = enabled,
            accessibilityLabel = label ?: placeholder,
            placeholder = placeholder?.let { { Text(it) } },
            leading = leadingIcon?.let { { Icon(it, contentDescription = null, modifier = Modifier.size(18.dp)) } },
            trailing = trailing,
            lineLimits = if (singleLine) TextFieldLineLimits.SingleLine else TextFieldLineLimits.MultiLine(minHeightInLines = minLines),
            keyboardOptions = keyboardOptions,
        )
    }
}

// ---------------------------------------------------------------- feedback

@Composable
fun NxDialog(
    onDismissRequest: () -> Unit,
    title: String,
    text: @Composable () -> Unit,
    confirmButton: @Composable () -> Unit,
    dismissButton: (@Composable () -> Unit)? = null,
    icon: ImageVector? = null,
) {
    AlertDialog(
        visible = true,
        onDismissRequest = onDismissRequest,
        icon = icon?.let { { NxIconWell(it, size = 44.dp) } },
        title = { Text(title, style = NxType.title) },
        text = text,
        positiveButton = confirmButton,
        negativeButton = dismissButton,
    )
}

/** Circular indeterminate spinner in the accent colour. */
@Composable
fun NxSpinner(modifier: Modifier = Modifier, size: Dp = 22.dp, color: Color = Nx.primary) {
    val transition = rememberInfiniteTransition(label = "spinner")
    val angle by transition.animateFloat(0f, 360f, infiniteRepeatable(tween(900, easing = LinearEasing), RepeatMode.Restart), label = "angle")
    Canvas(modifier.size(size)) {
        val stroke = this.size.minDimension * 0.12f
        drawArc(
            color = color,
            startAngle = angle,
            sweepAngle = 270f,
            useCenter = false,
            topLeft = Offset(stroke / 2, stroke / 2),
            size = Size(this.size.width - stroke, this.size.height - stroke),
            style = Stroke(width = stroke, cap = StrokeCap.Round),
        )
    }
}

/** Minimal snackbar replacement: one message at a time, auto-dismissed. */
@Stable
class NxSnackbarState {
    var message by mutableStateOf<String?>(null)
        private set
    private var serial by mutableStateOf(0)

    suspend fun showSnackbar(text: String) {
        message = text
        val mine = ++serial
        delay(2800)
        if (serial == mine) message = null
    }

    fun dismiss() {
        message = null
    }
}

@Composable
fun rememberNxSnackbarState(): NxSnackbarState = remember { NxSnackbarState() }

@Composable
fun NxSnackbarHost(state: NxSnackbarState, modifier: Modifier = Modifier) {
    var last by remember { mutableStateOf("") }
    state.message?.let { last = it }
    AnimatedVisibility(
        visible = state.message != null,
        modifier = modifier
            .windowInsetsPadding(WindowInsets.navigationBars)
            .padding(16.dp),
        enter = slideInVertically { it } + fadeIn(),
        exit = slideOutVertically { it } + fadeOut(),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Nx.panelRaised)
                .border(1.dp, Nx.primary.copy(alpha = 0.4f), RoundedCornerShape(16.dp))
                .clickable { state.dismiss() }
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(Modifier.size(8.dp).clip(CircleShape).background(Nx.primary))
            Text(last, style = NxType.body, color = Nx.onPanel)
        }
    }
}
