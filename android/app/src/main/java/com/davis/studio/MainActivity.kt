package com.davis.studio

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Bundle
import android.util.Base64
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import java.io.ByteArrayOutputStream

class MainActivity : AppCompatActivity() {

    private var videoUri: Uri? = null
    private var videoDurationSec = 0

    private lateinit var tvVideoInfo: TextView
    private lateinit var tvResult: TextView
    private lateinit var tvStatus: TextView
    private lateinit var etTopic: EditText
    private lateinit var btnAnalyze: Button
    private lateinit var progress: ProgressBar

    private val pickVideo =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                val uri = result.data?.data ?: return@registerForActivityResult
                try {
                    contentResolver.takePersistableUriPermission(
                        uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
                    )
                } catch (_: Exception) {
                }
                videoUri = uri
                loadVideoInfo(uri)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvVideoInfo = findViewById(R.id.tvVideoInfo)
        tvResult = findViewById(R.id.tvResult)
        tvStatus = findViewById(R.id.tvStatus)
        etTopic = findViewById(R.id.etTopic)
        btnAnalyze = findViewById(R.id.btnAnalyze)
        progress = findViewById(R.id.progress)

        findViewById<Button>(R.id.btnPick).setOnClickListener {
            val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "video/*"
            }
            pickVideo.launch(intent)
        }

        btnAnalyze.setOnClickListener { analyze() }
        findViewById<Button>(R.id.btnGenerate).setOnClickListener { generate() }
        findViewById<Button>(R.id.btnDownload).setOnClickListener { download() }
        findViewById<Button>(R.id.btnSettings).setOnClickListener { showSettings() }

        if (Prefs.claudeKey(this).isEmpty()) {
            status("Tip: open Settings and paste your Claude API key first.")
        }
    }

    private fun loadVideoInfo(uri: Uri) {
        try {
            val mmr = MediaMetadataRetriever()
            mmr.setDataSource(this, uri)
            val durMs =
                mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 0L
            val w = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH) ?: "?"
            val h = mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT) ?: "?"
            mmr.release()
            videoDurationSec = (durMs / 1000).toInt()
            tvVideoInfo.text = "Selected: ${videoDurationSec}s · ${w}x${h}"
            btnAnalyze.isEnabled = true
            status("")
        } catch (e: Exception) {
            tvVideoInfo.text = "Could not read video: ${e.message}"
        }
    }

    private fun analyze() {
        val uri = videoUri ?: return
        val key = Prefs.claudeKey(this)
        if (key.isEmpty()) {
            showSettings()
            status("Paste your Claude API key first.")
            return
        }
        setBusy(true)
        status("Extracting frames…")
        Thread {
            try {
                val frames = extractFrames(uri, 6)
                runOnUiThread { status("Asking Claude to study the video… (can take a minute)") }
                val result = ClaudeClient.analyze(key, frames, videoDurationSec)
                runOnUiThread {
                    tvResult.text = result
                    tvResult.visibility = View.VISIBLE
                    val topic = result.lineSequence()
                        .firstOrNull { it.startsWith("TOPIC:") }
                        ?.removePrefix("TOPIC:")?.trim()
                    if (!topic.isNullOrEmpty()) etTopic.setText(topic)
                    status("Analysis done. Review the blueprint, then Generate.")
                    setBusy(false)
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status("Analysis failed: ${e.message}")
                    setBusy(false)
                }
            }
        }.start()
    }

    private fun extractFrames(uri: Uri, count: Int): List<String> {
        val mmr = MediaMetadataRetriever()
        mmr.setDataSource(this, uri)
        val durMs =
            mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLong() ?: 1000L
        val frames = ArrayList<String>()
        for (i in 0 until count) {
            val tUs = (durMs * 1000L) * (2L * i + 1) / (2L * count)
            val bmp = mmr.getFrameAtTime(tUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                ?: continue
            val scale = 512f / maxOf(bmp.width, bmp.height)
            val scaled = if (scale < 1f) {
                Bitmap.createScaledBitmap(
                    bmp, (bmp.width * scale).toInt(), (bmp.height * scale).toInt(), true
                )
            } else bmp
            val baos = ByteArrayOutputStream()
            scaled.compress(Bitmap.CompressFormat.JPEG, 70, baos)
            frames.add(Base64.encodeToString(baos.toByteArray(), Base64.NO_WRAP))
        }
        mmr.release()
        if (frames.isEmpty()) throw RuntimeException("Could not extract frames from this video")
        return frames
    }

    private fun generate() {
        val topic = etTopic.text.toString().trim()
        if (topic.isEmpty()) {
            status("Analyze a video first, or type a topic yourself.")
            return
        }
        val token = Prefs.githubToken(this)
        if (token.isEmpty()) {
            showSettings()
            status("Paste your GitHub token first (needed to run the cloud pipeline).")
            return
        }
        setBusy(true)
        status("Starting cloud video generation…")
        Thread {
            try {
                GitHubApi.triggerPipeline(token, Prefs.repo(this), topic)
                runOnUiThread {
                    status("✅ Pipeline started! Your video will be ready in ~5 minutes. Then tap Download.")
                    setBusy(false)
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status("Generation failed: ${e.message}")
                    setBusy(false)
                }
            }
        }.start()
    }

    private fun download() {
        val token = Prefs.githubToken(this)
        if (token.isEmpty()) {
            showSettings()
            status("Paste your GitHub token first.")
            return
        }
        setBusy(true)
        status("Downloading latest video…")
        Thread {
            try {
                val name = GitHubApi.downloadLatestVideo(this, token, Prefs.repo(this))
                runOnUiThread {
                    status("✅ Saved to Movies/DavisStudio/$name — open your Gallery to watch it.")
                    setBusy(false)
                    Toast.makeText(this, "Video saved!", Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status("Download failed: ${e.message}")
                    setBusy(false)
                }
            }
        }.start()
    }

    private fun showSettings() {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }
        val etClaude = EditText(this).apply {
            hint = "Claude API key (sk-ant-…)"
            setText(Prefs.claudeKey(this@MainActivity))
        }
        val etGithub = EditText(this).apply {
            hint = "GitHub token (ghp_… or github_pat_…)"
            setText(Prefs.githubToken(this@MainActivity))
        }
        val etRepo = EditText(this).apply {
            hint = "GitHub repo (owner/name)"
            setText(Prefs.repo(this@MainActivity))
        }
        layout.addView(etClaude)
        layout.addView(etGithub)
        layout.addView(etRepo)

        AlertDialog.Builder(this)
            .setTitle("Settings")
            .setView(layout)
            .setPositiveButton("Save") { _, _ ->
                Prefs.save(
                    this,
                    etClaude.text.toString(),
                    etGithub.text.toString(),
                    etRepo.text.toString()
                )
                status("Settings saved.")
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun setBusy(busy: Boolean) {
        progress.visibility = if (busy) View.VISIBLE else View.GONE
        btnAnalyze.isEnabled = !busy && videoUri != null
    }

    private fun status(msg: String) {
        tvStatus.text = msg
    }
}
