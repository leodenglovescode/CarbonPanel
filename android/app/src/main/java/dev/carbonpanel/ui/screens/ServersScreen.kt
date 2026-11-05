package dev.carbonpanel.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.SavedServer
import dev.carbonpanel.ui.ServerPreview
import dev.carbonpanel.ui.ServersViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.components.LocalizedText as Text
import dev.carbonpanel.ui.theme.Info

@Composable
fun ServersScreen(servers: List<SavedServer>, viewModel: ServersViewModel, onSelect: (String) -> Unit, onSettings: () -> Unit) {
    val previews by viewModel.previews.collectAsStateWithLifecycle()
    LaunchedEffect(servers.map { it.id }) { viewModel.setServers(servers.map { it.id }) }
    LazyColumn(
        modifier = Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.safeDrawing),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Your servers", style = MaterialTheme.typography.headlineSmall)
                    Spacer(Modifier.height(6.dp))
                    MonoText("${servers.size} servers · live overview")
                }
                FilledTonalIconButton(onClick = onSettings) {
                    Icon(Icons.Default.Settings, contentDescription = localizeUiText("App settings"))
                }
            }
        }
        items(servers, key = { it.id }) { server -> ServerCard(server, previews[server.id]) { onSelect(server.id) } }
        item { MonoText("Live previews refresh every 15 seconds while this screen is open.") }
    }
}

@Composable
private fun ServerCard(server: SavedServer, preview: ServerPreview?, onOpen: () -> Unit) {
    val colors = MaterialTheme.colorScheme
    val online = preview?.online == true
    val tone = when {
        preview == null -> colors.onSurfaceVariant
        online -> colors.primary
        else -> colors.error
    }
    val status = when {
        preview == null -> "Connecting…"
        online -> "Online"
        else -> preview.error ?: "Unavailable"
    }
    Surface(shape = RoundedCornerShape(18.dp), color = colors.surface,
        border = BorderStroke(1.dp, colors.outlineVariant)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(Modifier.size(32.dp).clip(RoundedCornerShape(10.dp))
                    .background(colors.primary.copy(alpha = .10f)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Default.Dns, contentDescription = null,
                        tint = colors.primary, modifier = Modifier.size(18.dp))
                }
                Column(Modifier.weight(1f)) {
                    Text(server.name, style = MaterialTheme.typography.titleSmall,
                        maxLines = 1, overflow = TextOverflow.Ellipsis)
                    val endpoint = preview?.endpoint ?: server.endpoints.firstOrNull().orEmpty()
                    MonoText(endpoint.removePrefix("https://"), maxLines = 1)
                }
                Row(verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    Box(Modifier.size(5.dp).background(tone, CircleShape))
                    Text(status, style = MaterialTheme.typography.labelSmall, color = tone,
                        maxLines = 1, overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.widthIn(max = 100.dp))
                }
            }
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                val gaugeSize = ((maxWidth - 100.dp) / 3).coerceIn(44.dp, 56.dp)
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(Modifier.weight(1f), horizontalArrangement = Arrangement.SpaceBetween) {
                        MetricRing("CPU", preview?.snapshot?.cpu?.aggregate, Modifier.width(gaugeSize))
                        MetricRing("RAM", preview?.snapshot?.memory?.percent, Modifier.width(gaugeSize), Info)
                        MetricRing("DISK", preview?.storagePercent, Modifier.width(gaugeSize), colors.tertiary)
                    }
                    FilledTonalButton(onClick = onOpen, modifier = Modifier.heightIn(min = 48.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp), shape = RoundedCornerShape(12.dp)) {
                        Text("Open")
                        Spacer(Modifier.width(5.dp))
                        Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                    }
                }
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                when {
                    preview?.online == false && preview.snapshot != null -> MonoText("Last known readings")
                    preview?.snapshot?.system != null -> MonoText("Up ${formatUptime(preview.snapshot.system.uptime_seconds)}")
                    else -> MonoText(server.username, maxLines = 1)
                }
                if (server.endpoints.size > 1) MonoText("+${server.endpoints.size - 1} addresses")
            }
        }
    }
}
