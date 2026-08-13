package dev.carbonpanel.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.MaterialTheme
import dev.carbonpanel.ui.components.LocalizedText as Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.SiteResponse
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.Info
import dev.carbonpanel.ui.theme.Warning

@Composable
fun SitesScreen(viewModel: PanelViewModel, onOpenSite: (String) -> Unit) {
    val state by viewModel.sites.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadSites() }

    var confirm by remember { mutableStateOf<Triple<String, String, String>?>(null) }

    confirm?.let { (id, name, action) ->
        ConfirmDialog(
            title = "${action.replaceFirstChar { it.uppercase() }} site",
            body = "$action $name?",
            confirmLabel = action.replaceFirstChar { it.uppercase() },
            destructive = action != "start",
            onConfirm = { viewModel.siteAction(id, name, action) },
            onDismiss = { confirm = null },
        )
    }

    LoadList(
        state = state,
        onRefresh = { viewModel.loadSites(refresh = true) },
        emptyTitle = "No sites",
        emptyDetail = "Add sites from the web panel — they can be imported from nginx.",
    ) { sites ->
        items(sites, key = { it.id }) { site ->
            SiteRow(
                site = site,
                busy = site.id in busy,
                onAction = { confirm = Triple(site.id, site.name, it) },
                onOpen = { onOpenSite(site.id) },
            )
        }
    }
}

@Composable
private fun SiteRow(
    site: SiteResponse,
    busy: Boolean,
    onAction: (String) -> Unit,
    onOpen: () -> Unit,
) {
    PanelCard(modifier = Modifier.fillMaxWidth().clickable(onClick = onOpen)) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    site.name,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                MonoText("${site.type} · ${site.service_name}", maxLines = 1)
            }
            StatusPill((site.status?.status ?: "unknown").replaceFirstChar { it.uppercase() }, site.isRunning)
        }

        site.description?.takeIf { it.isNotBlank() }?.let { MonoText(it, maxLines = 2) }
        site.status?.uptime?.takeIf { it.isNotBlank() }?.let { MonoText("Since $it") }

        Row(
            horizontalArrangement = Arrangement.spacedBy(2.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (busy) {
                InlineSpinner()
            } else if (site.isRunning) {
                TextButton(onClick = { onAction("restart") }) { Text("Restart") }
                TextButton(onClick = { onAction("stop") }) { Text("Stop", color = Danger) }
            } else {
                TextButton(onClick = { onAction("start") }) { Text("Start", color = Accent) }
            }
            TextButton(onClick = onOpen) { Text("Details") }
        }
    }
}

@Composable
fun SiteDetailScreen(viewModel: PanelViewModel, siteId: String) {
    val sites by viewModel.sites.collectAsStateWithLifecycle()
    val config by viewModel.siteConfig.collectAsStateWithLifecycle()
    val traffic by viewModel.siteTraffic.collectAsStateWithLifecycle()

    LaunchedEffect(siteId) { viewModel.loadSiteDetail(siteId) }

    val site = sites.dataOrNull?.firstOrNull { it.id == siteId }

    androidx.compose.foundation.lazy.LazyColumn(
        modifier = Modifier.fillMaxWidth(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item {
            PanelCard {
                Text(site?.name ?: "Site", style = MaterialTheme.typography.titleMedium)
                site?.let {
                    DetailRow("Type", it.type)
                    DetailRow("Service", it.service_name)
                    DetailRow("Manager", it.service_manager)
                    it.config_file_path?.let { p -> DetailRow("Config", p) }
                    if (it.log_paths.isNotEmpty()) {
                        DetailRow("Logs", it.log_paths.joinToString("\n"))
                    }
                    it.status?.pid?.let { pid -> DetailRow("PID", pid.toString()) }
                }
            }
        }

        item { SectionLabel("Traffic — last hour") }
        item {
            LoadContent(traffic) { t ->
                PanelCard {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(
                            "${t.total_requests} requests",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        MonoText(formatBytes(t.total_bytes))
                    }
                    if (t.requests_per_minute.size >= 2) {
                        // Requests/min isn't a percentage, so it's normalised
                        // against its own peak before reusing the chart.
                        val peak = t.requests_per_minute.maxOf { it.count }.coerceAtLeast(1)
                        PercentChart(
                            series = listOf(
                                Series(
                                    "req",
                                    t.requests_per_minute.map { it.count * 100.0 / peak },
                                    Info,
                                ),
                            ),
                            height = 90,
                        )
                        MonoText("peak $peak req/min")
                    }
                    StackedBar(
                        listOf(
                            t.status_2xx to Accent,
                            t.status_3xx to Info,
                            t.status_4xx to Warning,
                            t.status_5xx to Danger,
                        ),
                    )
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        MonoText("2xx ${t.status_2xx}", color = Accent)
                        MonoText("3xx ${t.status_3xx}", color = Info)
                        MonoText("4xx ${t.status_4xx}", color = Warning)
                        MonoText("5xx ${t.status_5xx}", color = Danger)
                    }
                }
            }
        }

        traffic.dataOrNull?.takeIf { it.top_paths.isNotEmpty() }?.let { t ->
            item { SectionLabel("Top paths") }
            item {
                PanelCard {
                    t.top_paths.take(8).forEach { DetailRow(it.value, it.count.toString()) }
                }
            }
            if (t.top_ips.isNotEmpty()) {
                item { SectionLabel("Top clients") }
                item {
                    PanelCard {
                        t.top_ips.take(8).forEach { DetailRow(it.value, it.count.toString()) }
                    }
                }
            }
        }

        item { SectionLabel("Config") }
        item {
            LoadContent(config) { c ->
                PanelCard {
                    MonoText(c.path, maxLines = 1)
                    // Config files are wide; wrapping them destroys the
                    // structure that makes them readable, so scroll instead.
                    Row(Modifier.horizontalScroll(rememberScrollState())) {
                        Text(
                            c.content.take(20_000),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(vertical = 4.dp),
                        )
                    }
                }
            }
        }
    }
}
