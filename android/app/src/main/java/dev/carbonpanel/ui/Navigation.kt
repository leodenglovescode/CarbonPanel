package dev.carbonpanel.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Apps
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Memory
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Terminal
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * Every place the app can be.
 *
 * The five primary destinations are the ones worth reaching in one tap from a
 * phone; the rest live behind "More" rather than being crammed into a bottom
 * bar that stops being scannable past five items.
 */
enum class Dest(
    val route: String,
    val title: String,
    val icon: ImageVector,
    val primary: Boolean = false,
) {
    Dashboard("dashboard", "Status", Icons.Filled.Dashboard, primary = true),
    Docker("docker", "Docker", Icons.Filled.Inventory2, primary = true),
    Services("services", "Services", Icons.Filled.Dns, primary = true),
    Disks("disks", "Storage", Icons.Filled.Storage, primary = true),
    More("more", "More", Icons.Filled.MoreHoriz, primary = true),

    Sites("sites", "Sites", Icons.Filled.Language),
    Cron("cron", "Cron", Icons.Filled.Schedule),
    Apps("apps", "Ports", Icons.Filled.Apps),
    Processes("processes", "Processes", Icons.Filled.Memory),
    Sessions("sessions", "Shell sessions", Icons.Filled.Terminal),
    Bookmarks("bookmarks", "Bookmarks", Icons.Filled.Bookmark),
    Webhooks("webhooks", "Webhooks", Icons.Filled.Notifications),
    Logs("logs", "Update logs", Icons.AutoMirrored.Filled.List),
    Settings("settings", "Settings", Icons.Filled.Settings),
    ;

    companion object {
        val primaries = entries.filter { it.primary }
        val secondaries = entries.filter { !it.primary }
        fun byRoute(route: String?) = entries.firstOrNull { it.route == route }
    }
}

/** Route for a single site's detail page. */
fun siteDetailRoute(id: String) = "site/$id"
