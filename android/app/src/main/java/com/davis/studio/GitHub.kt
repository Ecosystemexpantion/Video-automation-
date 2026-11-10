package com.davis.studio

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.BufferedSink
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.concurrent.TimeUnit

class GitHubException(message: String) : Exception(message)

/** Talks to the GitHub repository that acts as Davis Studio's cloud backend. */
class GitHub(private val token: String, private val repo: String) {

    private fun request(url: String): Request.Builder = Request.Builder()
        .url(url)
        .header("Authorization", "Bearer $token")
        .header("Accept", "application/vnd.github+json")
        .header("X-GitHub-Api-Version", "2022-11-28")

    private fun explain(code: Int, body: String): String {
        val detail = try {
            JSONObject(body).optString("message")
        } catch (e: Exception) {
            ""
        }
        return when (code) {
            401 -> "GitHub rejected the token. Create a new one in Settings."
            403 -> "The token is not allowed to do this. It needs the \"repo\" permission."
            404 -> "Not found. Check the repository name and that the token can access it."
            else -> "GitHub error $code. $detail".trim()
        }
    }

    /** Confirms the token can write to the repo. Returns the repo's full name. */
    suspend fun checkAccess(): String = withContext(Dispatchers.IO) {
        http.newCall(request("$API/repos/$repo").build()).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            if (!resp.isSuccessful) throw GitHubException(explain(resp.code, body))
            val json = JSONObject(body)
            val canPush = json.optJSONObject("permissions")?.optBoolean("push", false) ?: false
            if (!canPush) {
                throw GitHubException("This token can read the repo but not write to it. Create it with the \"repo\" permission.")
            }
            json.optString("full_name", repo)
        }
    }

    /** Reads a file from the app-data branch. Returns null if it does not exist yet. */
    suspend fun readData(path: String): String? = withContext(Dispatchers.IO) {
        val req = request("$API/repos/$repo/contents/$path?ref=app-data")
            .header("Accept", "application/vnd.github.raw+json")
            .build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            when {
                resp.code == 404 -> null
                !resp.isSuccessful -> throw GitHubException(explain(resp.code, body))
                else -> body
            }
        }
    }

    /** Starts a cloud workflow. */
    suspend fun dispatch(workflow: String, inputs: Map<String, String>) = withContext(Dispatchers.IO) {
        val payload = JSONObject().put("ref", "main").put("inputs", JSONObject(inputs))
        val req = request("$API/repos/$repo/actions/workflows/$workflow/dispatches")
            .post(payload.toString().toRequestBody(JSON))
            .build()
        http.newCall(req).execute().use { resp ->
            if (resp.code != 204) {
                val body = resp.body?.string() ?: ""
                if (resp.code == 404) {
                    throw GitHubException("The cloud engine was not found in this repo, or the token cannot start it.")
                }
                throw GitHubException(explain(resp.code, body))
            }
        }
    }

    private fun inboxReleaseId(): Long {
        http.newCall(request("$API/repos/$repo/releases/tags/davis-inbox").build()).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            if (resp.isSuccessful) return JSONObject(body).getLong("id")
            if (resp.code != 404) throw GitHubException(explain(resp.code, body))
        }
        val payload = JSONObject()
            .put("tag_name", "davis-inbox")
            .put("name", "Davis Studio inbox")
            .put("body", "Reference uploads. Managed automatically.")
        val create = request("$API/repos/$repo/releases")
            .post(payload.toString().toRequestBody(JSON))
            .build()
        return http.newCall(create).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            if (!resp.isSuccessful) throw GitHubException(explain(resp.code, body))
            JSONObject(body).getLong("id")
        }
    }

    /**
     * Uploads the reference video at full quality (the original file, untouched)
     * to the repo's inbox, where the cloud engine picks it up.
     */
    suspend fun uploadReference(
        resolver: ContentResolver,
        cacheDir: File,
        uri: Uri,
        jobId: String,
        onProgress: (Float) -> Unit,
    ) = withContext(Dispatchers.IO) {
        val releaseId = inboxReleaseId()

        var size = -1L
        resolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { c ->
            if (c.moveToFirst() && !c.isNull(0)) size = c.getLong(0)
        }
        // GitHub needs the exact length up front; copy to a temp file if the picker did not report one.
        var temp: File? = null
        if (size <= 0) {
            val copy = File(cacheDir, "$jobId.upload")
            resolver.openInputStream(uri)?.use { input ->
                copy.outputStream().use { input.copyTo(it) }
            } ?: throw GitHubException("Could not open the selected video.")
            temp = copy
            size = copy.length()
        }
        if (size > MAX_UPLOAD_BYTES) {
            temp?.delete()
            throw GitHubException("This video is larger than 2 GB, which is the upload limit.")
        }

        val total = size
        val body = object : RequestBody() {
            override fun contentType() = "video/mp4".toMediaType()
            override fun contentLength() = total
            override fun writeTo(sink: BufferedSink) {
                val input = temp?.inputStream() ?: resolver.openInputStream(uri)
                    ?: throw GitHubException("Could not open the selected video.")
                input.use {
                    val buffer = ByteArray(128 * 1024)
                    var sent = 0L
                    while (true) {
                        val n = it.read(buffer)
                        if (n < 0) break
                        sink.write(buffer, 0, n)
                        sent += n
                        onProgress((sent.toDouble() / total).toFloat().coerceIn(0f, 1f))
                    }
                }
            }
        }

        try {
            val req = request("https://uploads.github.com/repos/$repo/releases/$releaseId/assets?name=$jobId.mp4")
                .post(body)
                .build()
            http.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    throw GitHubException(explain(resp.code, resp.body?.string() ?: ""))
                }
            }
        } finally {
            temp?.delete()
        }
    }

    companion object {
        private const val API = "https://api.github.com"
        private const val MAX_UPLOAD_BYTES = 2L * 1024 * 1024 * 1024
        private val JSON = "application/json".toMediaType()

        private val http = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(120, TimeUnit.SECONDS)
            .writeTimeout(120, TimeUnit.SECONDS)
            .build()
    }
}

/** Direct Claude call for Quick chat, used only when the owner has saved their own API key. */
object QuickChat {
    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(300, TimeUnit.SECONDS)
        .build()

    private const val SYSTEM = "You are Davis, a creative partner for short-form video. " +
        "Help with hooks, scripts, titles, captions and content strategy. " +
        "Reply for a phone screen: plain text, short paragraphs."

    suspend fun reply(apiKey: String, history: List<ChatMessage>): String = withContext(Dispatchers.IO) {
        val messages = JSONArray()
        history.filter { !it.isError }.forEach {
            messages.put(JSONObject().put("role", it.role).put("content", it.text))
        }
        val payload = JSONObject()
            .put("model", "claude-opus-4-8")
            .put("max_tokens", 4096)
            .put("thinking", JSONObject().put("type", "adaptive"))
            .put("system", SYSTEM)
            .put("messages", messages)
        val req = Request.Builder()
            .url("https://api.anthropic.com/v1/messages")
            .header("x-api-key", apiKey)
            .header("anthropic-version", "2023-06-01")
            .post(payload.toString().toRequestBody("application/json".toMediaType()))
            .build()
        http.newCall(req).execute().use { resp ->
            val body = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                val detail = try {
                    JSONObject(body).getJSONObject("error").getString("message")
                } catch (e: Exception) {
                    body.take(200)
                }
                throw GitHubException("Claude error ${resp.code}: $detail")
            }
            val json = JSONObject(body)
            if (json.optString("stop_reason") == "refusal") {
                throw GitHubException("Claude declined to answer that.")
            }
            val content = json.getJSONArray("content")
            val sb = StringBuilder()
            for (i in 0 until content.length()) {
                val block = content.getJSONObject(i)
                if (block.optString("type") == "text") sb.append(block.optString("text"))
            }
            sb.toString().trim()
        }
    }
}
