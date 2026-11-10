package com.davis.studio

import android.content.ContentValues
import android.content.Context
import android.provider.MediaStore
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit
import java.util.zip.ZipInputStream

object GitHubApi {

    private val http = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(600, TimeUnit.SECONDS)
        .build()

    /** Starts the cloud video pipeline with a custom topic. */
    fun triggerPipeline(token: String, repo: String, topic: String) {
        val body = JSONObject()
            .put("ref", "main")
            .put(
                "inputs", JSONObject()
                    .put("custom_topic", topic)
                    .put("platform", "all")
            )

        val request = Request.Builder()
            .url("https://api.github.com/repos/$repo/actions/workflows/video_pipeline.yml/dispatches")
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Accept", "application/vnd.github+json")
            .post(body.toString().toRequestBody("application/json".toMediaType()))
            .build()

        http.newCall(request).execute().use { resp ->
            if (resp.code != 204) {
                val text = resp.body?.string()?.take(300) ?: ""
                throw RuntimeException("GitHub dispatch failed (${resp.code}): $text")
            }
        }
    }

    /**
     * Downloads the newest generated video artifact and saves the mp4 into
     * Movies/DavisStudio. Returns the saved file name.
     */
    fun downloadLatestVideo(ctx: Context, token: String, repo: String): String {
        // 1. Find the newest generated-video artifact
        val listReq = Request.Builder()
            .url("https://api.github.com/repos/$repo/actions/artifacts?per_page=30")
            .addHeader("Authorization", "Bearer $token")
            .addHeader("Accept", "application/vnd.github+json")
            .build()

        var downloadUrl: String? = null
        var artifactName = ""
        http.newCall(listReq).execute().use { resp ->
            val text = resp.body?.string() ?: ""
            if (!resp.isSuccessful) {
                throw RuntimeException("GitHub artifacts list failed (${resp.code}): ${text.take(200)}")
            }
            val artifacts = JSONObject(text).getJSONArray("artifacts")
            for (i in 0 until artifacts.length()) {
                val a = artifacts.getJSONObject(i)
                if (a.getString("name").startsWith("generated-video") && !a.getBoolean("expired")) {
                    downloadUrl = a.getString("archive_download_url")
                    artifactName = a.getString("name")
                    break
                }
            }
        }
        val url = downloadUrl
            ?: throw RuntimeException("No generated videos found yet. Run the pipeline first.")

        // 2. Download the zip and extract the first mp4 straight into MediaStore
        val dlReq = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $token")
            .build()

        http.newCall(dlReq).execute().use { resp ->
            if (!resp.isSuccessful) {
                throw RuntimeException("Artifact download failed (${resp.code})")
            }
            val stream = resp.body?.byteStream()
                ?: throw RuntimeException("Empty artifact response")

            ZipInputStream(stream).use { zip ->
                var entry = zip.nextEntry
                while (entry != null) {
                    if (!entry.isDirectory && entry.name.endsWith(".mp4")) {
                        val fileName = "$artifactName.mp4"
                        val values = ContentValues().apply {
                            put(MediaStore.Video.Media.DISPLAY_NAME, fileName)
                            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
                            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/DavisStudio")
                            put(MediaStore.Video.Media.IS_PENDING, 1)
                        }
                        val resolver = ctx.contentResolver
                        val uri = resolver.insert(
                            MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values
                        ) ?: throw RuntimeException("Could not create video file")

                        resolver.openOutputStream(uri)?.use { out ->
                            val buf = ByteArray(64 * 1024)
                            while (true) {
                                val n = zip.read(buf)
                                if (n <= 0) break
                                out.write(buf, 0, n)
                            }
                        }
                        values.clear()
                        values.put(MediaStore.Video.Media.IS_PENDING, 0)
                        resolver.update(uri, values, null, null)
                        return fileName
                    }
                    entry = zip.nextEntry
                }
            }
        }
        throw RuntimeException("Artifact had no mp4 inside")
    }
}
