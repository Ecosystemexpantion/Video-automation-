package com.davis.studio

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.app.DownloadManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.widget.Toast
import coil.compose.AsyncImage

// ---------------- Create ----------------

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateScreen(vm: AppViewModel, onOpenLibrary: () -> Unit) {
    var mode by rememberSaveable { mutableIntStateOf(0) }
    var notes by rememberSaveable { mutableStateOf("") }
    var topic by rememberSaveable { mutableStateOf("") }
    var voice by rememberSaveable { mutableStateOf(vm.settings.voice) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if (uri != null) vm.pickVideo(uri)
    }
    val state = vm.createState
    val busy = state is CreateState.Uploading || state is CreateState.Starting

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
        Text("Create", color = TextHigh, fontSize = 30.sp, fontWeight = FontWeight.Bold)
        Text("Make a new video in your style.", color = TextLow, fontSize = 15.sp)
        Spacer(Modifier.height(16.dp))

        SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
            listOf("Replicate a video", "From a topic").forEachIndexed { i, label ->
                SegmentedButton(
                    selected = mode == i,
                    onClick = { mode = i; vm.clearCreateError() },
                    shape = SegmentedButtonDefaults.itemShape(i, 2),
                ) { Text(label) }
            }
        }

        if (mode == 0) {
            SectionLabel("Reference video")
            val p = vm.picked
            if (p == null) {
                Surface(
                    color = Panel, shape = MaterialTheme.shapes.medium, border = BorderStroke(1.dp, Line),
                    modifier = Modifier.fillMaxWidth().height(170.dp).clickable(enabled = !busy) {
                        picker.launch(androidx.activity.result.PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly))
                    },
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                        Icon(Icons.Filled.UploadFile, null, tint = Mint, modifier = Modifier.size(40.dp))
                        Spacer(Modifier.height(8.dp))
                        Text("Choose a video from your phone", color = TextHigh, fontWeight = FontWeight.SemiBold)
                        Text("Uploaded at full original quality", color = TextLow, fontSize = 13.sp)
                    }
                }
            } else {
                PanelCard {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (p.thumb != null) {
                            Image(p.thumb.asImageBitmap(), null, contentScale = ContentScale.Crop,
                                modifier = Modifier.size(72.dp, 110.dp).clip(RoundedCornerShape(10.dp)))
                        }
                        Spacer(Modifier.width(14.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Reference selected", color = TextHigh, fontWeight = FontWeight.SemiBold)
                            Text("${p.durationSec}s · ${p.width}×${p.height}", color = TextLow, fontSize = 13.sp)
                            if (p.sizeBytes > 0) Text("%.1f MB".format(p.sizeBytes / 1_048_576.0), color = TextLow, fontSize = 13.sp)
                        }
                        TextButton(onClick = {
                            picker.launch(androidx.activity.result.PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.VideoOnly))
                        }, enabled = !busy) { Text("Change") }
                    }
                }
            }
        } else {
            SectionLabel("Topic")
            OutlinedTextField(topic, { topic = it }, placeholder = { Text("e.g. 3 ways AI saves small businesses time") },
                modifier = Modifier.fillMaxWidth(), minLines = 2)
        }

        SectionLabel("Directions (optional)")
        OutlinedTextField(notes, { notes = it },
            placeholder = { Text(if (mode == 0) "e.g. Same style but about selling on Selar" else "e.g. Funny tone, end with a question") },
            modifier = Modifier.fillMaxWidth(), minLines = 2)

        SectionLabel("Voice")
        var open by remember { mutableStateOf(false) }
        ExposedDropdownMenuBox(open, { open = it }) {
            OutlinedTextField(VOICES.first { it.id == voice }.label, {}, readOnly = true,
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(open) },
                modifier = Modifier.menuAnchor().fillMaxWidth())
            ExposedDropdownMenu(open, { open = false }) {
                VOICES.forEach { v ->
                    DropdownMenuItem(text = { Text(v.label) }, onClick = { voice = v.id; vm.settings.voice = v.id; open = false })
                }
            }
        }

        Spacer(Modifier.height(20.dp))
        when (state) {
            is CreateState.Uploading -> {
                Text("Uploading reference… ${(state.fraction * 100).toInt()}%", color = Amber)
                LinearProgressIndicator({ state.fraction }, Modifier.fillMaxWidth().padding(top = 8.dp))
            }
            is CreateState.Starting -> Text("Starting the cloud engine…", color = Amber)
            is CreateState.Failed -> Notice(state.message, Danger)
            else -> {}
        }
        Spacer(Modifier.height(12.dp))
        Button(
            onClick = {
                if (mode == 0) vm.picked?.let { vm.replicate(it.uri, notes, voice) }
                else vm.createFromTopic(topic, notes, voice)
            },
            enabled = !busy && (if (mode == 0) vm.picked != null else topic.isNotBlank()),
            modifier = Modifier.fillMaxWidth().height(54.dp),
        ) {
            Icon(Icons.Filled.AutoAwesome, null); Spacer(Modifier.width(8.dp))
            Text(if (mode == 0) "Replicate this video" else "Generate video", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        }
        Text("Takes about 5–8 minutes in the cloud. You can close the app; it keeps going.",
            color = TextLow, fontSize = 12.sp, modifier = Modifier.padding(top = 10.dp))

        val active = vm.jobs.filter { it.isActive }
        if (active.isNotEmpty()) {
            SectionLabel("In progress")
            active.take(3).forEach { JobRow(it) { vm.showJob(it.id) }; Spacer(Modifier.height(8.dp)) }
            TextButton(onClick = onOpenLibrary) { Text("See all videos") }
        }
    }
}

// ---------------- Library ----------------

@Composable
fun JobRow(job: JobSummary, onClick: () -> Unit) {
    Surface(color = Panel, shape = MaterialTheme.shapes.medium, border = BorderStroke(1.dp, Line),
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(56.dp, 84.dp).clip(RoundedCornerShape(8.dp)).background(PanelHigh), contentAlignment = Alignment.Center) {
                if (job.thumbUrl != null) AsyncImage(job.thumbUrl, null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
                else Icon(if (job.isFailed) Icons.Filled.ErrorOutline else Icons.Filled.Movie, null, tint = TextLow)
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(job.title, color = TextHigh, fontWeight = FontWeight.SemiBold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                Text(
                    when { job.isActive -> job.step; job.isFailed -> job.error ?: "Failed"; else -> timeAgo(job.createdAt) },
                    color = if (job.isFailed) Danger else TextLow, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
                if (job.isActive) LinearProgressIndicator({ job.progress / 100f }, Modifier.fillMaxWidth().padding(top = 6.dp))
            }
            Spacer(Modifier.width(8.dp))
            StatusChip(job)
        }
    }
}

@Composable
fun LibraryScreen(vm: AppViewModel, onCreate: () -> Unit) {
    var filter by rememberSaveable { mutableIntStateOf(0) }
    val list = when (filter) { 1 -> vm.jobs.filter { it.isDone }; 2 -> vm.jobs.filter { it.isActive }; else -> vm.jobs }
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp)) {
        Row(Modifier.padding(top = 20.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("Library", color = TextHigh, fontSize = 30.sp, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            IconButton(onClick = { vm.refreshNow() }) {
                if (vm.jobsLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                else Icon(Icons.Filled.Refresh, "Refresh", tint = TextLow)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(vertical = 10.dp)) {
            listOf("All", "Ready", "In progress").forEachIndexed { i, l ->
                FilterChip(filter == i, { filter = i }, label = { Text(l) })
            }
        }
        vm.jobsError?.let { Notice(it, Danger); Spacer(Modifier.height(8.dp)) }
        if (list.isEmpty()) {
            Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                Icon(Icons.Filled.VideoLibrary, null, tint = TextLow, modifier = Modifier.size(48.dp))
                Text("No videos yet", color = TextHigh, modifier = Modifier.padding(top = 8.dp))
                TextButton(onClick = onCreate) { Text("Create your first video") }
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(bottom = 20.dp)) {
                items(list, key = { it.id }) { JobRow(it) { vm.showJob(it.id) } }
            }
        }
    }
}

// ---------------- Job detail ----------------

fun downloadVideo(context: Context, url: String, name: String) {
    try {
        val dm = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val req = DownloadManager.Request(Uri.parse(url))
            .setTitle(name)
            .setMimeType("video/mp4")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_MOVIES, "DavisStudio/$name")
        dm.enqueue(req)
        Toast.makeText(context, "Downloading to Movies/DavisStudio", Toast.LENGTH_LONG).show()
    } catch (e: Exception) {
        Toast.makeText(context, "Download failed: ${e.message}", Toast.LENGTH_LONG).show()
    }
}

fun shareText(context: Context, text: String) {
    context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text), "Share"))
}

@Composable
fun JobScreen(vm: AppViewModel) {
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val job = vm.openJob
    val summary = job?.summary ?: vm.jobs.firstOrNull { it.id == vm.openJobId }
    var remixOpen by remember { mutableStateOf(false) }
    var remixNotes by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().background(Ink)) {
        Row(Modifier.padding(8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = { vm.closeJob() }) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "Back", tint = TextHigh) }
            Text(summary?.title ?: "Video", color = TextHigh, fontSize = 18.sp, fontWeight = FontWeight.SemiBold,
                maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
            summary?.let { s ->
                IconButton(onClick = { vm.hideJob(s.id) }) { Icon(Icons.Filled.DeleteOutline, "Remove", tint = TextLow) }
            }
        }
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
            if (summary == null) { CircularProgressIndicator(Modifier.padding(40.dp)); return@Column }

            when {
                summary.isDone && summary.videoUrl != null -> {
                    VideoPlayer(summary.videoUrl, Modifier.fillMaxWidth().aspectRatio(9f / 16f).clip(MaterialTheme.shapes.medium).background(PanelHigh))
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button({ downloadVideo(context, summary.videoUrl, "${summary.id}.mp4") }, Modifier.weight(1f)) {
                            Icon(Icons.Filled.Download, null); Spacer(Modifier.width(6.dp)); Text("Save HD")
                        }
                        OutlinedButton({ shareText(context, summary.videoUrl) }, Modifier.weight(1f)) {
                            Icon(Icons.Filled.Share, null); Spacer(Modifier.width(6.dp)); Text("Share")
                        }
                    }
                    OutlinedButton({ remixOpen = !remixOpen }, Modifier.fillMaxWidth().padding(top = 8.dp)) {
                        Icon(Icons.Filled.Shuffle, null); Spacer(Modifier.width(6.dp)); Text("Remix / make another version")
                    }
                    if (remixOpen && job != null) {
                        OutlinedTextField(remixNotes, { remixNotes = it }, placeholder = { Text("What should change? (optional)") },
                            modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                        Button({ vm.remix(job, remixNotes); remixOpen = false }, Modifier.fillMaxWidth().padding(top = 8.dp)) { Text("Start remix") }
                    }
                }
                summary.isFailed -> PanelCard {
                    Text("This video failed", color = Danger, fontWeight = FontWeight.Bold)
                    Text(summary.error ?: "Unknown error", color = TextHigh, modifier = Modifier.padding(top = 6.dp))
                    if (job?.runUrl?.isNotEmpty() == true) TextButton({ openUrl(context, job.runUrl) }) { Text("Open the cloud log") }
                }
                else -> PanelCard {
                    Text(summary.step.ifEmpty { "Queued" }, color = Amber, fontWeight = FontWeight.SemiBold)
                    LinearProgressIndicator({ summary.progress / 100f }, Modifier.fillMaxWidth().padding(vertical = 10.dp))
                    Text("${summary.progress}% · updates automatically. You can leave this screen.", color = TextLow, fontSize = 13.sp)
                }
            }

            if (job != null) {
                if (job.refDurationSec > 0) {
                    SectionLabel("Reference")
                    PanelCard {
                        Text("${"%.1f".format(job.refDurationSec)}s · ${job.refSceneCount} scenes detected", color = TextHigh)
                        if (job.refTranscript.isNotBlank()) Text("“${job.refTranscript.take(400)}”", color = TextLow, fontSize = 13.sp, modifier = Modifier.padding(top = 6.dp))
                    }
                }
                if (job.styleAnalysis.isNotEmpty()) {
                    SectionLabel("Style Davis copied")
                    PanelCard { job.styleAnalysis.forEach { Text("• $it", color = TextHigh, fontSize = 14.sp, modifier = Modifier.padding(vertical = 2.dp)) } }
                }
                if (job.scenes.isNotEmpty()) {
                    SectionLabel("Shot list · ${job.scenes.size} scenes")
                    job.scenes.forEachIndexed { i, s ->
                        PanelCard(Modifier.padding(bottom = 8.dp)) {
                            Text("Scene ${i + 1} · ${s.visualQuery}", color = Mint, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                            Text(s.narration, color = TextHigh, modifier = Modifier.padding(top = 4.dp))
                            if (s.onScreenText.isNotBlank()) Text("On screen: ${s.onScreenText}", color = TextLow, fontSize = 12.sp)
                        }
                    }
                    SectionLabel("Post caption")
                    val caption = job.description + "\n\n" + job.hashtags.joinToString(" ") { "#$it" }
                    PanelCard {
                        SelectionContainer { Text(caption, color = TextHigh, fontSize = 14.sp) }
                        Row {
                            TextButton({ clipboard.setText(AnnotatedString(caption)); Toast.makeText(context, "Copied", Toast.LENGTH_SHORT).show() }) { Text("Copy caption") }
                            TextButton({ clipboard.setText(AnnotatedString(job.script)); Toast.makeText(context, "Copied", Toast.LENGTH_SHORT).show() }) { Text("Copy script") }
                        }
                    }
                }
            }
            Spacer(Modifier.height(30.dp))
        }
    }
}

// ---------------- Davis chat ----------------

@Composable
fun ChatScreen(vm: AppViewModel) {
    var quick by rememberSaveable { mutableStateOf(false) }
    var input by rememberSaveable { mutableStateOf("") }
    LaunchedEffect(Unit) { vm.loadChat() }
    val messages = if (quick) vm.quickChat else vm.chat
    val busy = if (quick) vm.quickBusy else vm.chatBusy
    val listState = rememberLazyListState()
    LaunchedEffect(messages.size, busy) { if (messages.isNotEmpty()) listState.animateScrollToItem(messages.size) }

    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        Row(Modifier.padding(top = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Davis", color = TextHigh, fontSize = 30.sp, fontWeight = FontWeight.Bold)
                Text(if (quick) "Quick ideas with Claude" else "Claude Code on your repo, from your phone", color = TextLow, fontSize = 13.sp)
            }
            IconButton(onClick = { if (quick) vm.clearQuickChat() else vm.newChat() }) { Icon(Icons.Filled.AddComment, "New chat", tint = TextLow) }
        }
        Row(Modifier.padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(!quick, { quick = false }, label = { Text("Agent") }, leadingIcon = { Icon(Icons.Filled.Code, null, Modifier.size(16.dp)) })
            FilterChip(quick, { quick = true }, label = { Text("Quick") }, leadingIcon = { Icon(Icons.Filled.Bolt, null, Modifier.size(16.dp)) })
        }
        if (quick && vm.settings.claudeKey.isEmpty()) {
            Notice("Quick mode needs your own Claude API key (Settings). Agent mode works without it.", Amber)
        }
        LazyColumn(Modifier.weight(1f), state = listState, verticalArrangement = Arrangement.spacedBy(8.dp), contentPadding = PaddingValues(vertical = 8.dp)) {
            if (messages.isEmpty()) item {
                PanelCard {
                    Text(if (quick) "Ask for hooks, scripts, titles or content ideas." else
                        "Ask Davis to do anything you'd do with Claude Code on a laptop: change the video style, fix a bug, add a feature, explain the code. Changes are saved to your repo.",
                        color = TextLow, fontSize = 14.sp)
                }
            }
            items(messages.size) { i ->
                val m = messages[i]
                val mine = m.role == "user"
                Row(Modifier.fillMaxWidth(), horizontalArrangement = if (mine) Arrangement.End else Arrangement.Start) {
                    Surface(
                        color = when { mine -> Mint.copy(alpha = 0.18f); m.isError -> Danger.copy(alpha = 0.14f); else -> Panel },
                        shape = RoundedCornerShape(16.dp), modifier = Modifier.widthIn(max = 320.dp),
                    ) { SelectionContainer { Text(m.text, color = TextHigh, fontSize = 15.sp, modifier = Modifier.padding(12.dp)) } }
                }
            }
            if (busy) item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                    Text(if (quick) "  Thinking…" else "  Davis is working in the cloud (1–5 min)…", color = TextLow, fontSize = 13.sp)
                }
            }
        }
        Row(Modifier.padding(vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(input, { input = it }, placeholder = { Text("Message Davis") }, modifier = Modifier.weight(1f), maxLines = 5)
            IconButton(onClick = { if (quick) vm.sendQuick(input) else vm.sendToAgent(input); input = "" }, enabled = !busy && input.isNotBlank()) {
                Icon(Icons.AutoMirrored.Filled.Send, "Send", tint = if (!busy && input.isNotBlank()) Mint else TextLow)
            }
        }
    }
}

// ---------------- Settings ----------------

@Composable
fun SettingsScreen(vm: AppViewModel) {
    val context = LocalContext.current
    var key by rememberSaveable { mutableStateOf(vm.settings.claudeKey) }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp)) {
        Text("Settings", color = TextHigh, fontSize = 30.sp, fontWeight = FontWeight.Bold)
        SectionLabel("Connection")
        PanelCard {
            Text("Connected to", color = TextLow, fontSize = 13.sp)
            Text(vm.settings.repo, color = TextHigh, fontWeight = FontWeight.SemiBold)
            Row {
                TextButton({ openUrl(context, "https://github.com/${vm.settings.repo}/actions") }) { Text("Cloud runs") }
                TextButton({ vm.disconnect() }) { Text("Disconnect", color = Danger) }
            }
        }
        SectionLabel("Claude API key (optional)")
        PanelCard {
            Text("Only needed for Quick chat. Video creation and Agent chat use the key stored in your repo's secrets (ANTHROPIC_API_KEY).", color = TextLow, fontSize = 13.sp)
            OutlinedTextField(key, { key = it }, label = { Text("sk-ant-…") }, singleLine = true,
                visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
            TextButton({ vm.settings.claudeKey = key; Toast.makeText(context, "Saved", Toast.LENGTH_SHORT).show() }) { Text("Save key") }
        }
        SectionLabel("Updates")
        PanelCard {
            Text("Version ${BuildConfigVersion}", color = TextHigh)
            TextButton({ openUrl(context, "https://github.com/${vm.settings.repo}/releases/download/davis-studio-latest/davis-studio.apk") }) { Text("Download latest version") }
        }
    }
}

const val BuildConfigVersion = "2.0"
