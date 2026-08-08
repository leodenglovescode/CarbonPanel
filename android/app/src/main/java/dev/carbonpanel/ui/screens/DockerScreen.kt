package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
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
import dev.carbonpanel.data.ContainerInfo
import dev.carbonpanel.ui.Load
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Danger

@Composable
fun DockerScreen(viewModel: PanelViewModel) {
    val state by viewModel.containers.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()
    val query by viewModel.dockerQuery.collectAsStateWithLifecycle()

    // Fetched on entry and on pull, not polled: containers change when someone
    // acts on them, so a poll loop here would be battery spent re-fetching an
    // identical list.
    LaunchedEffect(Unit) { viewModel.loadContainers() }

    var confirm by remember { mutableStateOf<Triple<String, String, String>?>(null) }

    confirm?.let { (id, name, action) ->
        ConfirmDialog(
            title = "${action.replaceFirstChar { it.uppercase() }} container",
            body = "$action $name?",
            confirmLabel = action.replaceFirstChar { it.uppercase() },
            destructive = action != "start",
            onConfirm = { viewModel.containerAction(id, name, action) },
            onDismiss = { confirm = null },
        )
    }

    // Matched against name and image, since "which container runs postgres"
    // is as common a question as knowing what it was named.
    val filtered = (state.dataOrNull ?: emptyList()).filter {
        query.isBlank() ||
            it.name.contains(query, ignoreCase = true) ||
            it.image.contains(query, ignoreCase = true)
    }
    val display = when (val s = state) {
        is Load.Ok -> Load.Ok(filtered, s.refreshing)
        else -> state
    }

    LoadList(
        state = display,
        onRefresh = { viewModel.loadContainers(refresh = true) },
        emptyTitle = if (query.isNotBlank()) "No matches" else "No containers",
        emptyDetail = if (query.isNotBlank()) "No container matches \"$query\"."
                      else "Either none exist, or Docker isn't available on the server.",
        header = {
            item {
                SearchField(
                    value = query,
                    onValueChange = viewModel::setDockerQuery,
                    placeholder = "Search containers…",
                )
            }
        },
    ) { containers ->
        val (running, stopped) = containers.partition { it.isRunning }
        if (running.isNotEmpty()) {
            item { SectionLabel("RUNNING · ${running.size}") }
            items(running, key = { it.id }) {
                ContainerRow(it, it.id in busy) { a -> confirm = Triple(it.id, it.name, a) }
            }
        }
        if (stopped.isNotEmpty()) {
            item { SectionLabel("STOPPED · ${stopped.size}") }
            items(stopped, key = { it.id }) {
                ContainerRow(it, it.id in busy) { a -> confirm = Triple(it.id, it.name, a) }
            }
        }
    }
}

@Composable
private fun ContainerRow(
    container: ContainerInfo,
    busy: Boolean,
    onAction: (String) -> Unit,
) {
    PanelCard(modifier = Modifier.fillMaxWidth()) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    container.name,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                MonoText(container.image, maxLines = 1)
            }
            StatusPill(container.state.replaceFirstChar { it.uppercase() }, container.isRunning)
        }

        if (container.isRunning) {
            MonoText(
                "%.1f%% CPU · %s / %s".format(
                    container.cpu_percent,
                    formatMb(container.mem_usage_mb),
                    formatMb(container.mem_limit_mb),
                ),
            )
            if (container.mem_limit_mb > 0) Meter(container.mem_percent, height = 3)
        } else {
            MonoText(container.status, maxLines = 1)
        }

        if (container.ports.isNotBlank()) MonoText(container.ports, maxLines = 2)

        Row(
            horizontalArrangement = Arrangement.spacedBy(2.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (busy) {
                InlineSpinner()
            } else if (container.isRunning) {
                TextButton(onClick = { onAction("restart") }) { Text("Restart") }
                TextButton(onClick = { onAction("stop") }) {
                    Text("Stop", color = Danger)
                }
            } else {
                TextButton(onClick = { onAction("start") }) {
                    Text("Start", color = Accent)
                }
            }
        }
    }
}
