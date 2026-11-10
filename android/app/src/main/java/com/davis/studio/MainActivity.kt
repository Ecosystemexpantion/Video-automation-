package com.davis.studio

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Forum
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel

const val TOKEN_URL = "https://github.com/settings/tokens/new?scopes=repo&description=Davis%20Studio"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            DavisTheme {
                val vm: AppViewModel = viewModel()
                DavisApp(vm)
            }
        }
    }
}

@Composable
fun DavisApp(vm: AppViewModel) {
    if (!vm.connected) {
        SetupScreen(vm)
        return
    }

    var tab by rememberSaveable { mutableIntStateOf(0) }

    if (vm.openJobId != null) {
        BackHandler { vm.closeJob() }
        JobScreen(vm)
        return
    }

    Scaffold(
        containerColor = Ink,
        bottomBar = {
            NavigationBar(containerColor = Panel) {
                val items = listOf(
                    "Create" to Icons.Filled.AutoAwesome,
                    "Library" to Icons.Filled.VideoLibrary,
                    "Davis" to Icons.Filled.Forum,
                    "Settings" to Icons.Filled.Settings,
                )
                items.forEachIndexed { index, (label, icon) ->
                    NavigationBarItem(
                        selected = tab == index,
                        onClick = { tab = index },
                        icon = { Icon(icon, contentDescription = label) },
                        label = { Text(label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MintDark,
                            selectedTextColor = Mint,
                            indicatorColor = Mint,
                            unselectedIconColor = TextLow,
                            unselectedTextColor = TextLow,
                        ),
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when (tab) {
                0 -> CreateScreen(vm, onOpenLibrary = { tab = 1 })
                1 -> LibraryScreen(vm, onCreate = { tab = 0 })
                2 -> ChatScreen(vm)
                else -> SettingsScreen(vm)
            }
        }
    }
}

@Composable
fun SetupScreen(vm: AppViewModel) {
    val context = LocalContext.current
    var token by rememberSaveable { mutableStateOf("") }
    var repo by rememberSaveable { mutableStateOf(vm.settings.repo) }

    Column(
        Modifier
            .fillMaxSize()
            .background(Ink)
            .verticalScroll(rememberScrollState())
            .padding(24.dp)
    ) {
        Spacer(Modifier.height(32.dp))
        Box(
            Modifier
                .size(64.dp)
                .background(Mint, RoundedCornerShape(18.dp)),
            contentAlignment = Alignment.Center,
        ) {
            Text("D", color = MintDark, fontSize = 34.sp, fontWeight = FontWeight.Black)
        }
        Spacer(Modifier.height(20.dp))
        Text("Davis Studio", color = TextHigh, fontSize = 32.sp, fontWeight = FontWeight.Bold)
        Text(
            "Give it a video. It studies the style and makes you a new one.",
            color = TextLow, fontSize = 16.sp, modifier = Modifier.padding(top = 6.dp),
        )

        SectionLabel("One-time setup")
        PanelCard {
            Text(
                "Davis Studio renders your videos on your own GitHub account, for free. " +
                    "It needs one key to reach it.",
                color = TextHigh, fontSize = 14.sp,
            )
            Spacer(Modifier.height(14.dp))
            Text("1.  Tap the button and sign in to GitHub.", color = TextLow, fontSize = 14.sp)
            Text("2.  Scroll down and tap \"Generate token\".", color = TextLow, fontSize = 14.sp)
            Text("3.  Copy the token and paste it below.", color = TextLow, fontSize = 14.sp)
            Spacer(Modifier.height(14.dp))
            OutlinedButton(onClick = { openUrl(context, TOKEN_URL) }, modifier = Modifier.fillMaxWidth()) {
                Text("Create my GitHub token")
            }
        }

        Spacer(Modifier.height(16.dp))
        OutlinedTextField(
            value = token,
            onValueChange = { token = it },
            label = { Text("GitHub token") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        Spacer(Modifier.height(10.dp))
        OutlinedTextField(
            value = repo,
            onValueChange = { repo = it },
            label = { Text("Repository") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        vm.connectError?.let {
            Spacer(Modifier.height(12.dp))
            Notice(it, Danger)
        }

        Spacer(Modifier.height(18.dp))
        Button(
            onClick = { vm.connect(token, repo) },
            enabled = !vm.connecting,
            modifier = Modifier.fillMaxWidth().height(52.dp),
        ) {
            if (vm.connecting) {
                CircularProgressIndicator(Modifier.size(22.dp), color = MintDark, strokeWidth = 2.dp)
            } else {
                Text("Connect", fontWeight = FontWeight.Bold, fontSize = 16.sp)
            }
        }
        Text(
            "The token stays on this phone. You do not need a Claude API key: " +
                "the cloud engine already has one.",
            color = TextLow, fontSize = 12.sp, modifier = Modifier.padding(top = 12.dp),
        )
    }
}
