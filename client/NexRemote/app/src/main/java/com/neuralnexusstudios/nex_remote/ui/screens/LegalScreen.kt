package com.neuralnexusstudios.nex_remote.ui.screens

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.neuralnexusstudios.nex_remote.core.AppContainer

@OptIn(ExperimentalMaterial3Api::class)
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

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Welcome to NexRemote") })
        },
        bottomBar = {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    Checkbox(checked = agreed, onCheckedChange = { agreed = it })
                    Text(
                        text = "I have read and agree to the Terms of Service and Privacy Policy.",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(top = 12.dp),
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                ) {
                    OutlinedButton(onClick = { (context as? Activity)?.finish() }) {
                        Text("Decline & Exit")
                    }
                    Button(
                        enabled = agreed,
                        onClick = {
                            appContainer.preferences.recordTermsAccepted()
                            onAccepted()
                        },
                        modifier = Modifier.padding(start = 12.dp),
                    ) {
                        Text("I Accept")
                    }
                }
            }
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize(),
        ) {
            TabRow(selectedTabIndex = selectedTab) {
                Tab(selected = selectedTab == 0, onClick = { selectedTab = 0 }, text = { Text("Terms") })
                Tab(selected = selectedTab == 1, onClick = { selectedTab = 1 }, text = { Text("Privacy") })
            }
            Text(
                text = if (selectedTab == 0) terms else privacy,
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}
