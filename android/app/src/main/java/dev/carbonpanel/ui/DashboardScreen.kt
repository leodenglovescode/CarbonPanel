package dev.carbonpanel.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.repo.PollState
import dev.carbonpanel.ui.theme.Danger
import dev.carbonpanel.ui.theme.Warning

@Composable
fun DashboardScreen(viewModel: PanelViewModel) {
    val state by viewModel.metrics.collectAsStateWithLifecycle()

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp),
    ) {
        when (val s = state) {
            is PollState.Connecting -> item {
                Text("Connecting…", style = MaterialTheme.typography.bodySmall)
            }

            is PollState.Error -> item {
                BannerRow(s.message, Danger)
            }

            is PollState.Unpaired -> item {
                BannerRow("Not paired with a server.", Warning)
            }

            is PollState.Connected -> {
                val snap = s.snapshot
                item { HeaderRow(snap, s.endpoint) }
                item { CpuMemoryRow(snap) }
                snap.gpu?.takeIf { it.available }?.devices?.firstOrNull()?.let { gpu ->
                    item {
                        MetricCard(
                            label = "GPU · ${gpu.name}",
                            value = "%.0f%%".format(gpu.utilization_percent),
                            percent = gpu.utilization_percent,
                            detail = "%.0f/%.0f MB · %.0f°C · %.0f W".format(
                                gpu.memory_used_mb, gpu.memory_total_mb,
                                gpu.temperature_c, gpu.power_draw_w,
                            ),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
                if (snap.disks.isNotEmpty()) {
                    item {
                        Text(
                            "DISKS",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(top = 6.dp),
                        )
                    }
                    items(snap.disks, key = { it.mountpoint }) { disk ->
                        MetricCard(
                            label = disk.mountpoint,
                            value = "%.0f%%".format(disk.usage_percent),
                            percent = disk.usage_percent,
                            detail = "%.0f / %.0f GB · %s".format(
                                disk.used_gb, disk.total_gb, disk.device,
                            ),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HeaderRow(snap: MetricsSnapshot, endpoint: String) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            snap.system?.hostname.orEmpty().ifBlank { "server" },
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            buildString {
                snap.system?.let { append("up ${formatUptime(it.uptime_seconds)}") }
                append(" · ")
                append(endpoint.removePrefix("http://").removePrefix("https://"))
            },
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun CpuMemoryRow(snap: MetricsSnapshot) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        snap.cpu?.let { cpu ->
            MetricCard(
                label = "CPU",
                value = "%.0f%%".format(cpu.aggregate),
                percent = cpu.aggregate,
                detail = cpu.temps.firstOrNull()?.let { "%.0f°C".format(it.temp_c) }
                    ?: cpu.load_avg.take(3).joinToString(" ") { "%.2f".format(it) },
                modifier = Modifier.weight(1f),
            )
        }
        snap.memory?.let { mem ->
            MetricCard(
                label = "RAM",
                value = "%.0f%%".format(mem.percent),
                percent = mem.percent,
                detail = "${formatGb(mem.used_mb)} / ${formatGb(mem.total_mb)}",
                modifier = Modifier.weight(1f),
            )
        }
    }
}
