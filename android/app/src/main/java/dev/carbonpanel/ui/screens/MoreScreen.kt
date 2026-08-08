package dev.carbonpanel.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import dev.carbonpanel.ui.Dest
import dev.carbonpanel.ui.components.MonoText
import dev.carbonpanel.ui.components.PanelCard
import dev.carbonpanel.ui.components.SectionLabel

@Composable
fun MoreScreen(onNavigate: (Dest) -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxWidth(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        item { SectionLabel("Everything else") }
        items(Dest.secondaries.size) { i ->
            val dest = Dest.secondaries[i]
            PanelCard(
                Modifier.fillMaxWidth().clickable { onNavigate(dest) },
                spacing = 2,
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Icon(
                            dest.icon,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(18.dp),
                        )
                        Column {
                            Text(dest.title, style = MaterialTheme.typography.bodyMedium)
                            MonoText(descriptionFor(dest))
                        }
                    }
                    Icon(
                        Icons.AutoMirrored.Filled.KeyboardArrowRight,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(18.dp),
                    )
                }
            }
        }
    }
}

private fun descriptionFor(dest: Dest): String = when (dest) {
    Dest.Sites -> "nginx sites, config and traffic"
    Dest.Cron -> "Scheduled jobs, managed and system"
    Dest.Apps -> "What's listening, and on which port"
    Dest.Processes -> "Top processes by CPU or memory"
    Dest.Sessions -> "Who's logged in over SSH"
    Dest.Bookmarks -> "Your saved links"
    Dest.Webhooks -> "Alert delivery endpoints"
    Dest.Logs -> "journalctl for the update services"
    Dest.Settings -> "Server addresses, theme, account"
    else -> ""
}
