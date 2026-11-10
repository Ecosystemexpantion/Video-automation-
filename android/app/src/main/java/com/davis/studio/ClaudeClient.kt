package com.davis.studio

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

object ClaudeClient {

    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(300, TimeUnit.SECONDS)
        .build()

    private const val PROMPT = """You are an expert short-form video strategist. The images are frames sampled evenly from a reference video (duration: %d seconds).

Study the reference carefully: its hook style, pacing, visual style, caption style, structure, emotional tone, and what makes it engaging.

Then produce a replication blueprint so I can recreate a video in the SAME style but about AI automation / making money online with AI.

Format your answer EXACTLY like this:

TOPIC: <one punchy line describing the new video to make, same angle and energy as the reference>

== STYLE ANALYSIS ==
<what the reference does: hook, pacing, visuals, captions, tone — short bullets>

== REPLICATED SCRIPT ==
<the full 30-45 second spoken script for the new video, matching the reference's structure beat for beat>

== SCENE PLAN ==
<numbered scenes: what should be on screen during each part, matching the reference's visual style>

== CAPTION STYLE ==
<how captions should look and behave, copied from the reference>"""

    /** Sends frames + prompt to Claude, returns the analysis text. */
    fun analyze(apiKey: String, framesBase64: List<String>, durationSec: Int): String {
        val content = JSONArray()
        for (frame in framesBase64) {
            content.put(
                JSONObject()
                    .put("type", "image")
                    .put(
                        "source", JSONObject()
                            .put("type", "base64")
                            .put("media_type", "image/jpeg")
                            .put("data", frame)
                    )
            )
        }
        content.put(
            JSONObject()
                .put("type", "text")
                .put("text", String.format(PROMPT, durationSec))
        )

        val body = JSONObject()
            .put("model", "claude-opus-4-8")
            .put("max_tokens", 4096)
            .put("thinking", JSONObject().put("type", "adaptive"))
            .put(
                "messages", JSONArray().put(
                    JSONObject().put("role", "user").put("content", content)
                )
            )

        val request = Request.Builder()
            .url("https://api.anthropic.com/v1/messages")
            .addHeader("x-api-key", apiKey)
            .addHeader("anthropic-version", "2023-06-01")
            .addHeader("content-type", "application/json")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()

        http.newCall(request).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                val msg = try {
                    JSONObject(text).getJSONObject("error").getString("message")
                } catch (e: Exception) {
                    text.take(300)
                }
                throw RuntimeException("Claude API error ${resp.code}: $msg")
            }
            val json = JSONObject(text)
            if (json.optString("stop_reason") == "refusal") {
                throw RuntimeException("Claude declined to analyze this video.")
            }
            val parts = json.getJSONArray("content")
            val sb = StringBuilder()
            for (i in 0 until parts.length()) {
                val block = parts.getJSONObject(i)
                if (block.getString("type") == "text") sb.append(block.getString("text"))
            }
            return sb.toString().trim()
        }
    }
}
