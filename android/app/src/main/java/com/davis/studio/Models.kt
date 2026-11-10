package com.davis.studio

import org.json.JSONArray
import org.json.JSONObject

data class JobSummary(
    val id: String,
    val createdAt: Long,
    val mode: String,
    val status: String,
    val step: String,
    val progress: Int,
    val title: String,
    val topic: String,
    val error: String?,
    val videoUrl: String?,
    val thumbUrl: String?,
) {
    val isActive: Boolean get() = status == "queued" || status == "running"
    val isDone: Boolean get() = status == "done"
    val isFailed: Boolean get() = status == "failed"

    fun toJson(): JSONObject = JSONObject()
        .put("id", id)
        .put("created_at", createdAt)
        .put("mode", mode)
        .put("status", status)
        .put("step", step)
        .put("progress", progress)
        .put("title", title)
        .put("topic", topic)
        .put("error", error ?: JSONObject.NULL)
        .put("video_url", videoUrl ?: JSONObject.NULL)
        .put("thumb_url", thumbUrl ?: JSONObject.NULL)
}

data class Scene(
    val narration: String,
    val visualQuery: String,
    val onScreenText: String,
)

data class Job(
    val summary: JobSummary,
    val styleAnalysis: List<String>,
    val scenes: List<Scene>,
    val description: String,
    val hashtags: List<String>,
    val runUrl: String,
    val voice: String,
    val notes: String,
    val durationSec: Double,
    val refDurationSec: Double,
    val refSceneCount: Int,
    val refTranscript: String,
) {
    val script: String get() = scenes.joinToString(" ") { it.narration }
}

data class ChatMessage(
    val role: String,
    val text: String,
    val isError: Boolean = false,
)

fun JSONObject.str(key: String): String? =
    if (!has(key) || isNull(key)) null else optString(key)

private fun JSONArray?.strings(): List<String> {
    if (this == null) return emptyList()
    return (0 until length()).map { optString(it) }
}

fun parseSummary(o: JSONObject): JobSummary = JobSummary(
    id = o.str("id") ?: "",
    createdAt = o.optLong("created_at", 0L),
    mode = o.str("mode") ?: "topic",
    status = o.str("status") ?: "queued",
    step = o.str("step") ?: "",
    progress = o.optInt("progress", 0),
    title = o.str("title") ?: "New video",
    topic = o.str("topic") ?: "",
    error = o.str("error"),
    videoUrl = o.str("video_url"),
    thumbUrl = o.str("thumb_url"),
)

fun parseIndex(raw: String): List<JobSummary> {
    val arr = JSONObject(raw).optJSONArray("jobs") ?: return emptyList()
    return (0 until arr.length()).map { parseSummary(arr.getJSONObject(it)) }
}

fun parseJob(raw: String): Job {
    val o = JSONObject(raw)
    val bp = o.optJSONObject("blueprint")
    val ref = o.optJSONObject("reference")
    val sceneArr = bp?.optJSONArray("scenes")
    val scenes = if (sceneArr == null) emptyList() else (0 until sceneArr.length()).map {
        val s = sceneArr.getJSONObject(it)
        Scene(
            narration = s.str("narration") ?: "",
            visualQuery = s.str("visual_query") ?: "",
            onScreenText = s.str("on_screen_text") ?: "",
        )
    }
    return Job(
        summary = parseSummary(o),
        styleAnalysis = bp?.optJSONArray("style_analysis").strings(),
        scenes = scenes,
        description = bp?.str("description") ?: "",
        hashtags = bp?.optJSONArray("hashtags").strings(),
        runUrl = o.str("run_url") ?: "",
        voice = o.str("voice") ?: "af_heart",
        notes = o.str("notes") ?: "",
        durationSec = o.optDouble("duration", 0.0),
        refDurationSec = ref?.optDouble("duration", 0.0) ?: 0.0,
        refSceneCount = ref?.optInt("scene_count", 0) ?: 0,
        refTranscript = ref?.str("transcript") ?: "",
    )
}

fun parseChat(raw: String): Pair<List<ChatMessage>, Boolean> {
    val o = JSONObject(raw)
    val arr = o.optJSONArray("messages") ?: JSONArray()
    val messages = (0 until arr.length()).map {
        val m = arr.getJSONObject(it)
        ChatMessage(
            role = m.str("role") ?: "assistant",
            text = m.str("text") ?: "",
            isError = m.optBoolean("error", false),
        )
    }
    return messages to o.optBoolean("pending", false)
}

data class VoiceOption(val id: String, val label: String)

val VOICES = listOf(
    VoiceOption("af_heart", "Heart · warm female"),
    VoiceOption("af_bella", "Bella · bright female"),
    VoiceOption("af_nicole", "Nicole · soft female"),
    VoiceOption("am_michael", "Michael · natural male"),
    VoiceOption("am_adam", "Adam · deep male"),
    VoiceOption("am_fenrir", "Fenrir · bold male"),
    VoiceOption("bf_emma", "Emma · British female"),
    VoiceOption("bm_george", "George · British male"),
)
