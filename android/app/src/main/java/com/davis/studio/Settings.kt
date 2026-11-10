package com.davis.studio

import android.content.Context
import org.json.JSONArray
import java.util.UUID

class Settings(context: Context) {
    private val sp = context.getSharedPreferences("davis_studio", Context.MODE_PRIVATE)

    var token: String
        get() = sp.getString("github_token", "") ?: ""
        set(value) = sp.edit().putString("github_token", value.trim()).apply()

    var repo: String
        get() = sp.getString("repo", DEFAULT_REPO) ?: DEFAULT_REPO
        set(value) = sp.edit().putString("repo", value.trim().trim('/')).apply()

    /** Optional. Only used for Quick chat; the cloud engine has its own key. */
    var claudeKey: String
        get() = sp.getString("claude_key", "") ?: ""
        set(value) = sp.edit().putString("claude_key", value.trim()).apply()

    var voice: String
        get() = sp.getString("voice", "af_heart") ?: "af_heart"
        set(value) = sp.edit().putString("voice", value).apply()

    var chatId: String
        get() {
            val existing = sp.getString("chat_id", null)
            if (existing != null) return existing
            return newChatId()
        }
        set(value) = sp.edit().putString("chat_id", value).apply()

    fun newChatId(): String {
        val id = "chat-" + UUID.randomUUID().toString().take(8)
        chatId = id
        return id
    }

    /** Jobs started on this phone that the cloud has not reported on yet. */
    var pendingJobs: List<JobSummary>
        get() = try {
            val arr = JSONArray(sp.getString("pending_jobs", "[]"))
            (0 until arr.length()).map { parseSummary(arr.getJSONObject(it)) }
        } catch (e: Exception) {
            emptyList()
        }
        set(value) {
            val arr = JSONArray()
            value.forEach { arr.put(it.toJson()) }
            sp.edit().putString("pending_jobs", arr.toString()).apply()
        }

    var hiddenJobs: Set<String>
        get() = sp.getStringSet("hidden_jobs", emptySet()) ?: emptySet()
        set(value) = sp.edit().putStringSet("hidden_jobs", value).apply()

    companion object {
        const val DEFAULT_REPO = "Ecosystemexpantion/Video-automation-"
    }
}
