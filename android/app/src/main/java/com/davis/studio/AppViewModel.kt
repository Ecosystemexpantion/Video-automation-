package com.davis.studio

import android.app.Application
import android.net.Uri
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job as CoroutineJob
import kotlinx.coroutines.withContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class PickedVideo(
    val uri: Uri,
    val thumb: Bitmap?,
    val durationSec: Int,
    val width: Int,
    val height: Int,
    val sizeBytes: Long,
)

sealed class CreateState {
    data object Idle : CreateState()
    data class Uploading(val fraction: Float) : CreateState()
    data object Starting : CreateState()
    data class Failed(val message: String) : CreateState()
}

class AppViewModel(app: Application) : AndroidViewModel(app) {

    val settings = Settings(app)

    var connected by mutableStateOf(settings.token.isNotEmpty())
        private set
    var connecting by mutableStateOf(false)
        private set
    var connectError by mutableStateOf<String?>(null)
        private set

    var jobs by mutableStateOf(settings.pendingJobs)
        private set
    var jobsLoading by mutableStateOf(false)
        private set
    var jobsError by mutableStateOf<String?>(null)
        private set

    var openJobId by mutableStateOf<String?>(null)
        private set
    var openJob by mutableStateOf<Job?>(null)
        private set

    var createState by mutableStateOf<CreateState>(CreateState.Idle)
        private set
    var picked by mutableStateOf<PickedVideo?>(null)
        private set

    var chat by mutableStateOf(listOf<ChatMessage>())
        private set
    var chatBusy by mutableStateOf(false)
        private set
    var quickChat by mutableStateOf(listOf<ChatMessage>())
        private set
    var quickBusy by mutableStateOf(false)
        private set
    private var remoteChatCount = 0
    private var chatLoaded = false

    private var pollLoop: CoroutineJob? = null

    private fun gh() = GitHub(settings.token, settings.repo)

    init {
        if (connected) startPolling()
    }

    // ---------- connection ----------

    fun connect(token: String, repo: String, onSuccess: () -> Unit = {}) {
        if (token.isBlank()) {
            connectError = "Paste your GitHub token first."
            return
        }
        connecting = true
        connectError = null
        viewModelScope.launch {
            try {
                GitHub(token.trim(), repo.trim().trim('/')).checkAccess()
                settings.token = token
                settings.repo = repo
                connected = true
                startPolling()
                onSuccess()
            } catch (e: Exception) {
                connectError = e.message ?: "Could not connect."
            } finally {
                connecting = false
            }
        }
    }

    fun disconnect() {
        pollLoop?.cancel()
        settings.token = ""
        connected = false
        jobs = emptyList()
        chat = emptyList()
        chatLoaded = false
    }

    // ---------- jobs ----------

    private fun startPolling() {
        pollLoop?.cancel()
        pollLoop = viewModelScope.launch {
            while (isActive) {
                refreshJobs(silent = true)
                // Poll quickly while something is rendering, slowly otherwise.
                delay(if (jobs.any { it.isActive }) 6_000 else 30_000)
            }
        }
    }

    fun refreshNow() {
        viewModelScope.launch { refreshJobs(silent = false) }
    }

    private suspend fun refreshJobs(silent: Boolean) {
        if (!connected) return
        if (!silent) jobsLoading = true
        try {
            val remote = gh().readData("index.json")?.let { parseIndex(it) } ?: emptyList()
            val remoteIds = remote.map { it.id }.toSet()
            val now = System.currentTimeMillis() / 1000

            // Keep phone-side placeholders until the cloud reports the job itself.
            val pending = settings.pendingJobs
                .filter { it.id !in remoteIds }
                .map {
                    if (it.isActive && now - it.createdAt > 15 * 60) {
                        it.copy(
                            status = "failed",
                            error = "The cloud run never started. Open the repo's Actions tab to see why.",
                        )
                    } else it
                }
            settings.pendingJobs = pending

            val hidden = settings.hiddenJobs
            jobs = (pending + remote)
                .filter { it.id !in hidden && !it.id.startsWith("selftest-") }
                .sortedByDescending { it.createdAt }
            jobsError = null

            val id = openJobId
            if (id != null && (openJob == null || openJob?.summary?.isActive == true || id !in remoteIds)) {
                loadJob(id)
            }
        } catch (e: Exception) {
            jobsError = e.message ?: "Could not load your videos."
        } finally {
            jobsLoading = false
        }
    }

    private suspend fun loadJob(id: String) {
        val raw = gh().readData("jobs/$id.json") ?: return
        if (openJobId == id) openJob = parseJob(raw)
    }

    fun showJob(id: String) {
        openJobId = id
        openJob = null
        viewModelScope.launch {
            try {
                loadJob(id)
            } catch (e: Exception) {
                jobsError = e.message
            }
        }
    }

    fun closeJob() {
        openJobId = null
        openJob = null
    }

    fun hideJob(id: String) {
        settings.hiddenJobs = settings.hiddenJobs + id
        settings.pendingJobs = settings.pendingJobs.filter { it.id != id }
        jobs = jobs.filter { it.id != id }
        if (openJobId == id) closeJob()
    }

    private fun newJobId(): String {
        val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
        val suffix = (1..3).map { "abcdefghjkmnpqrstuvwxyz23456789".random() }.joinToString("")
        return "v$stamp-$suffix"
    }

    private fun addPending(id: String, mode: String, title: String, topic: String) {
        val stub = JobSummary(
            id = id,
            createdAt = System.currentTimeMillis() / 1000,
            mode = mode,
            status = "queued",
            step = "Waiting for the cloud engine to start",
            progress = 2,
            title = title,
            topic = topic,
            error = null,
            videoUrl = null,
            thumbUrl = null,
        )
        settings.pendingJobs = listOf(stub) + settings.pendingJobs
        jobs = listOf(stub) + jobs
        startPolling()
    }

    fun pickVideo(uri: Uri) {
        clearCreateError()
        viewModelScope.launch {
            picked = withContext(Dispatchers.IO) {
                val app = getApplication<Application>()
                var size = 0L
                try {
                    app.contentResolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { c ->
                        if (c.moveToFirst() && !c.isNull(0)) size = c.getLong(0)
                    }
                } catch (e: Exception) {
                }
                val mmr = MediaMetadataRetriever()
                try {
                    mmr.setDataSource(app, uri)
                    fun meta(key: Int) = mmr.extractMetadata(key)?.toLongOrNull() ?: 0L
                    var w = meta(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH).toInt()
                    var h = meta(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT).toInt()
                    val rotation = meta(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION).toInt()
                    if (rotation == 90 || rotation == 270) {
                        val t = w; w = h; h = t
                    }
                    val frame = mmr.getFrameAtTime(1_000_000, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                    val thumb = frame?.let {
                        val scale = 480f / maxOf(it.width, it.height)
                        if (scale < 1f) {
                            Bitmap.createScaledBitmap(it, (it.width * scale).toInt(), (it.height * scale).toInt(), true)
                        } else it
                    }
                    PickedVideo(
                        uri = uri,
                        thumb = thumb,
                        durationSec = (meta(MediaMetadataRetriever.METADATA_KEY_DURATION) / 1000).toInt(),
                        width = w,
                        height = h,
                        sizeBytes = size,
                    )
                } catch (e: Exception) {
                    PickedVideo(uri, null, 0, 0, 0, size)
                } finally {
                    try {
                        mmr.release()
                    } catch (e: Exception) {
                    }
                }
            }
        }
    }

    fun clearPicked() {
        picked = null
    }

    /** Uploads the reference at original quality and starts a replication job. */
    fun replicate(uri: Uri, notes: String, voice: String) {
        if (createState is CreateState.Uploading || createState is CreateState.Starting) return
        val id = newJobId()
        createState = CreateState.Uploading(0f)
        viewModelScope.launch {
            try {
                val app = getApplication<Application>()
                gh().uploadReference(app.contentResolver, app.cacheDir, uri, id) { fraction ->
                    createState = CreateState.Uploading(fraction)
                }
                createState = CreateState.Starting
                gh().dispatch(
                    "studio_job.yml",
                    mapOf("job_id" to id, "mode" to "replicate", "notes" to notes.trim(), "voice" to voice),
                )
                addPending(id, "replicate", "Replicating your video", notes.trim())
                createState = CreateState.Idle
                picked = null
                showJob(id)
            } catch (e: Exception) {
                createState = CreateState.Failed(e.message ?: "Upload failed.")
            }
        }
    }

    fun createFromTopic(topic: String, notes: String, voice: String) {
        if (createState is CreateState.Starting) return
        val id = newJobId()
        createState = CreateState.Starting
        viewModelScope.launch {
            try {
                gh().dispatch(
                    "studio_job.yml",
                    mapOf(
                        "job_id" to id, "mode" to "topic", "topic" to topic.trim(),
                        "notes" to notes.trim(), "voice" to voice,
                    ),
                )
                addPending(id, "topic", topic.trim().take(60), topic.trim())
                createState = CreateState.Idle
                showJob(id)
            } catch (e: Exception) {
                createState = CreateState.Failed(e.message ?: "Could not start the video.")
            }
        }
    }

    /** A fresh take on an existing video, optionally with new directions. */
    fun remix(source: Job, notes: String) {
        val id = newJobId()
        viewModelScope.launch {
            try {
                gh().dispatch(
                    "studio_job.yml",
                    mapOf(
                        "job_id" to id, "mode" to "remix", "source_job" to source.summary.id,
                        "notes" to notes.trim(), "voice" to source.voice,
                    ),
                )
                addPending(id, "remix", "Remix: ${source.summary.title}".take(60), source.summary.topic)
                showJob(id)
            } catch (e: Exception) {
                jobsError = e.message ?: "Could not start the remix."
            }
        }
    }

    fun clearCreateError() {
        if (createState is CreateState.Failed) createState = CreateState.Idle
    }

    // ---------- chat ----------

    fun loadChat() {
        if (chatLoaded || !connected) return
        chatLoaded = true
        viewModelScope.launch {
            try {
                val raw = gh().readData("chats/${settings.chatId}.json") ?: return@launch
                val (messages, pending) = parseChat(raw)
                chat = messages
                remoteChatCount = messages.size
                if (pending) awaitReply()
            } catch (e: Exception) {
                chatLoaded = false
            }
        }
    }

    fun newChat() {
        if (chatBusy) return
        settings.newChatId()
        chat = emptyList()
        remoteChatCount = 0
    }

    /** Agent mode: Davis works on the repo in the cloud. */
    fun sendToAgent(text: String) {
        if (chatBusy || text.isBlank()) return
        chat = chat + ChatMessage("user", text.trim())
        chatBusy = true
        viewModelScope.launch {
            try {
                gh().dispatch(
                    "davis_chat.yml",
                    mapOf("chat_id" to settings.chatId, "message" to text.trim()),
                )
                remoteChatCount += 1
                awaitReply()
            } catch (e: Exception) {
                chat = chat + ChatMessage("assistant", e.message ?: "Could not reach Davis.", isError = true)
                chatBusy = false
            }
        }
    }

    private suspend fun awaitReply() {
        chatBusy = true
        try {
            // Up to 25 minutes: the agent can take a while on real code changes.
            repeat(250) {
                delay(6_000)
                val raw = try {
                    gh().readData("chats/${settings.chatId}.json")
                } catch (e: Exception) {
                    null
                }
                if (raw != null) {
                    val (messages, pending) = parseChat(raw)
                    if (!pending && messages.size > remoteChatCount) {
                        chat = messages
                        remoteChatCount = messages.size
                        return
                    }
                }
            }
            chat = chat + ChatMessage(
                "assistant",
                "Davis did not answer in time. Check the repo's Actions tab for the Davis Chat run.",
                isError = true,
            )
        } finally {
            chatBusy = false
        }
    }

    /** Quick mode: an instant answer straight from Claude, using the owner's own key. */
    fun sendQuick(text: String) {
        if (quickBusy || text.isBlank()) return
        val history = quickChat + ChatMessage("user", text.trim())
        quickChat = history
        quickBusy = true
        viewModelScope.launch {
            try {
                val reply = QuickChat.reply(settings.claudeKey, history)
                quickChat = quickChat + ChatMessage("assistant", reply)
            } catch (e: Exception) {
                quickChat = quickChat + ChatMessage("assistant", e.message ?: "Claude did not answer.", isError = true)
            } finally {
                quickBusy = false
            }
        }
    }

    fun clearQuickChat() {
        if (!quickBusy) quickChat = emptyList()
    }
}
