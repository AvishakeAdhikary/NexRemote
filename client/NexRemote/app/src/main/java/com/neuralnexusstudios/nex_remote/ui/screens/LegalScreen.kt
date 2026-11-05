package com.neuralnexusstudios.nex_remote.ui.screens

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.composables.ui.components.Checkbox
import com.composables.ui.components.Text
import com.neuralnexusstudios.nex_remote.core.AppContainer
import com.neuralnexusstudios.nex_remote.ui.design.Nx
import com.neuralnexusstudios.nex_remote.ui.design.NxButton
import com.neuralnexusstudios.nex_remote.ui.design.NxButtonKind
import com.neuralnexusstudios.nex_remote.ui.design.NxCard
import com.neuralnexusstudios.nex_remote.ui.design.NxScaffold
import com.neuralnexusstudios.nex_remote.ui.design.NxSegmented
import com.neuralnexusstudios.nex_remote.ui.design.NxType

@Composable
fun LegalScreen(
    appContainer: AppContainer,
    onAccepted: () -> Unit,
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableIntStateOf(0) }
    var agreed by remember { mutableStateOf(false) }
    var terms by remember { mutableStateOf("") }
    var privacy by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        terms = context.assets.open("legal/terms_of_service.txt").bufferedReader().use { it.readText() }
        privacy = context.assets.open("legal/privacy_policy.txt").bufferedReader().use { it.readText() }
    }

    NxScaffold(title = "Welcome to NexRemote") {
        Column(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                "Before you start, please read how NexRemote works and what stays on your devices.",
                style = NxType.body,
                color = Nx.muted,
            )
            NxSegmented(
                options = listOf("Terms of Service", "Privacy Policy"),
                selectedIndex = selectedTab,
                onSelect = { selectedTab = it },
                modifier = Modifier.fillMaxWidth(),
            )
            NxCard(Modifier.fillMaxWidth().weight(1f), contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp)) {
                Text(
                    text = if (selectedTab == 0) terms else privacy,
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(18.dp),
                    style = NxType.bodySmall,
                )
            }
            Row(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(Nx.panel)
                    .clickable { agreed = !agreed }
                    .padding(horizontal = 14.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Checkbox(checked = agreed, onCheckedChange = { agreed = it }, accessibilityLabel = "Agree to terms")
                Text("I have read and agree to the Terms of Service and Privacy Policy.", style = NxType.bodySmall)
            }
            Row(Modifier.fillMaxWidth().padding(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                NxButton(
                    "Decline & exit",
                    onClick = { (context as? Activity)?.finish() },
                    kind = NxButtonKind.Outlined,
                    modifier = Modifier.weight(1f),
                )
                NxButton(
                    "I accept",
                    enabled = agreed,
                    onClick = {
                        appContainer.preferences.recordTermsAccepted()
                        onAccepted()
                    },
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
