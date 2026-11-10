package com.davis.studio

import android.content.Context
import android.content.SharedPreferences

object Prefs {
    private fun sp(ctx: Context): SharedPreferences =
        ctx.getSharedPreferences("davis_studio", Context.MODE_PRIVATE)

    fun claudeKey(ctx: Context): String = sp(ctx).getString("claude_key", "") ?: ""
    fun githubToken(ctx: Context): String = sp(ctx).getString("github_token", "") ?: ""
    fun repo(ctx: Context): String =
        sp(ctx).getString("repo", "Ecosystemexpantion/Video-automation-") ?: ""

    fun save(ctx: Context, claudeKey: String, githubToken: String, repo: String) {
        sp(ctx).edit()
            .putString("claude_key", claudeKey.trim())
            .putString("github_token", githubToken.trim())
            .putString("repo", repo.trim())
            .apply()
    }
}
