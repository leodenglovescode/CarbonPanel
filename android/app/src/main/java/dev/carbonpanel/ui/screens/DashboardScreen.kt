package dev.carbonpanel.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
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
import dev.carbonpanel.data.MetricsSnapshot
import dev.carbonpanel.repo.PollState
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Accent
import dev.carbonpanel.ui.theme.Info
import dev.carbonpanel.ui.theme.NumericStyle
import dev.carbonpanel.ui.theme.Warning

@Composable
fun DashboardScreen(viewModel: PanelViewModel) {
    val state by viewModel.metrics.collectAsStateWithLifecycle()
    val history by viewModel.history.collectAsStateWithLifecycle()
    val diskState by viewModel.disks.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        viewModel.loadHistory()
        viewModel.loadDisks()
    }

    // Keep the chart moving without a second poll loop: every live snapshot
    // extends the series the server already gave us.
    LaunchedEffect(state) {
        (state as? PollState.Connected)?.let { viewModel.appendHistory(it.snapshot) }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        when (val s = state) {
            is PollState.Connecting -> item { LoadingBlock(label = "Connecting…") }
            is PollState.Unpaired -> item { InfoBanner("Not paired with a server") }
            is PollState.Error -> item { ErrorBanner(s.message) }
            is PollState.Connected -> {
                val snap = s.snapshot
                item { HostHeader(snap, s.endpoint) }
                item { CpuMemoryRow(snap) }
                // GPU sits with the other live gauges, above the history chart —
                // it's a current-state readout, not part of the trace.
                snap.gpu?.takeIf { it.available }?.devices?.forEach { gpu ->
                    item { GpuCard(gpu) }
                }
                if (history.size >= 2) item { HistoryCard(history) }
                if (snap.network.isNotEmpty()) item { NetworkCard(snap) }

                // Storage comes from /disks, not from the metrics snapshot.
                // The snapshot's disk list is psutil.disk_partitions with no
                // fstype and no is_virtual field, so snap and overlay mounts
                // cannot be reliably identified in it — and this screen showing
                // a different set of disks than the Storage screen is a bug in
                // itself. Disks also change slowly, so fetching once on entry
                // is cheaper than carrying them in every 0.4s poll.
                val physical = diskState.dataOrNull
                    ?.filterNot { it.is_virtual || isPseudoMount(it.mountpoint, it.device, it.fstype) }
                    .orEmpty()
                if (physical.isNotEmpty()) {
                    item { SectionLabel("Physical disks") }
                    items(physical, key = { it.mountpoint }) { disk ->
                        PanelCard(spacing = 6) {
                            Row(
                                Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(
                                        disk.mountpoint,
                                        style = MaterialTheme.typography.bodyMedium,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                    MonoText("${disk.device} · ${disk.fstype}", maxLines = 1)
                                }
                                Text(
                                    "%.0f%%".format(disk.usage_percent),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = usageColor(disk.usage_percent),
                                )
                            }
                            Meter(disk.usage_percent)
                            MonoText(
                                "${formatGb(disk.used_gb)} of ${formatGb(disk.total_gb)}",
                            )
                        }
                    }
                }
            }
        }
    }
}

/**
 * Compact status line under the app bar.
 *
 * Deliberately does not repeat the hostname — the app bar already shows it, and
 * printing it twice wasted the most valuable row on the screen. What isn't
 * anywhere else is how long the box has been up and which address the app
 * actually reached it on, which matters when several are configured.
 */
@Composable
private fun HostHeader(snap: MetricsSnapshot, endpoint: String) {
    Column(
        Modifier.fillMaxWidth().padding(horizontal = 2.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        ClockRow("Server", serverClock(snap), Accent)
        ClockRow("Phone", phoneClock(), MaterialTheme.colorScheme.onSurfaceVariant)
        Row(
            Modifier.fillMaxWidth().padding(top = 2.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            MonoText(snap.system?.let { "Up ${formatUptime(it.uptime_seconds)}" } ?: "")
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Canvas(Modifier.size(5.dp)) { drawCircle(Accent) }
                MonoText(endpoint.substringAfter("://"))
            }
        }
    }
}

@Composable
private fun ClockRow(label: String, value: String, tone: androidx.compose.ui.graphics.Color) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        MonoText(label)
        Text(value, style = MaterialTheme.typography.bodySmall, color = tone, maxLines = 1)
    }
}

/**
 * Server wall clock, rendered in the server's own zone.
 *
 * `ts` is epoch seconds, so formatting it with the phone's zone would just
 * restate phone time — the point of showing both is the zone difference (and
 * any clock skew), which needs the server's offset explicitly.
 */
private fun serverClock(snap: MetricsSnapshot): String {
    val sys = snap.system ?: return "—"
    if (snap.ts <= 0) return "—"
    val zone = java.util.TimeZone.getTimeZone(
        java.time.ZoneOffset.ofTotalSeconds(sys.utc_offset_seconds),
    )
    val fmt = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).apply {
        timeZone = zone
    }
    val stamp = fmt.format(java.util.Date((snap.ts * 1000).toLong()))
    val label = sys.timezone.ifBlank { "UTC" }
    return "$stamp $label ${offsetLabel(sys.utc_offset_seconds)}"
}

private fun phoneClock(): String {
    val now = java.util.Date()
    val fmt = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US)
    val offsetSeconds = java.util.TimeZone.getDefault().getOffset(now.time) / 1000
    val name = java.util.TimeZone.getDefault()
        .getDisplayName(false, java.util.TimeZone.SHORT, java.util.Locale.US)
    return "${fmt.format(now)} $name ${offsetLabel(offsetSeconds)}"
}

private fun offsetLabel(totalSeconds: Int): String {
    val sign = if (totalSeconds < 0) "-" else "+"
    val abs = kotlin.math.abs(totalSeconds)
    val h = abs / 3600
    val m = (abs % 3600) / 60
    return if (m == 0) "UTC$sign$h" else "UTC$sign$h:%02d".format(m)
}

@Composable
private fun CpuMemoryRow(snap: MetricsSnapshot) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        snap.cpu?.let { cpu ->
            BigMetricCard(
                label = "CPU",
                percent = cpu.aggregate,
                detail = cpu.temps.firstOrNull()?.let { "%.0f°C".format(it.temp_c) }
                    ?: cpu.load_avg.take(3).joinToString(" ") { "%.2f".format(it) },
                modifier = Modifier.weight(1f),
            )
        }
        snap.memory?.let { mem ->
            BigMetricCard(
                label = "RAM",
                percent = mem.percent,
                detail = "${formatMb(mem.used_mb)} / ${formatMb(mem.total_mb)}",
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun BigMetricCard(
    label: String,
    percent: Double,
    detail: String,
    modifier: Modifier = Modifier,
) {
    PanelCard(modifier = modifier) {
        SectionLabel(label)
        Text(
            "%.0f%%".format(percent),
            style = NumericStyle,
            color = usageColor(percent),
        )
        Meter(percent)
        MonoText(detail, maxLines = 1)
    }
}

@Composable
private fun HistoryCard(history: List<dev.carbonpanel.data.HistoryPoint>) {
    PanelCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SectionLabel("Last ${history.size} samples")
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                LegendDot("CPU", Accent)
                LegendDot("MEM", Info)
                if (history.any { it.gpu != null }) LegendDot("GPU", Warning)
            }
        }
        PercentChart(
            series = buildList {
                add(Series("cpu", history.map { it.cpu }, Accent))
                add(Series("mem", history.map { it.mem }, Info))
                if (history.any { it.gpu != null }) {
                    add(Series("gpu", history.map { it.gpu ?: 0.0 }, Warning))
                }
            },
        )
    }
}

@Composable
private fun LegendDot(label: String, color: androidx.compose.ui.graphics.Color) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Canvas(Modifier.size(6.dp)) { drawCircle(color) }
        Text(label, style = MaterialTheme.typography.labelSmall, color = color)
    }
}

@Composable
private fun GpuCard(gpu: dev.carbonpanel.data.GpuDevice) {
    PanelCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                gpu.name.ifBlank { "GPU ${gpu.index}" },
                style = MaterialTheme.typography.bodyMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            Text(
                "%.0f%%".format(gpu.utilization_percent),
                style = MaterialTheme.typography.bodyMedium,
                color = usageColor(gpu.utilization_percent),
            )
        }
        Meter(gpu.utilization_percent)
        MonoText(
            "${formatMb(gpu.memory_used_mb)} / ${formatMb(gpu.memory_total_mb)} · " +
                "%.0f°C · %.0f W".format(gpu.temperature_c, gpu.power_draw_w),
        )
    }
}

// Container plumbing. A Docker host has one of these per container plus the
// bridges, and they drowned out the interfaces anyone actually cares about —
// filtering by "has traffic" doesn't help, because they all do.
private val VIRTUAL_IFACE_PREFIXES =
    listOf("veth", "br-", "docker", "virbr", "vmnet", "lo")

private fun isVirtualIface(name: String) =
    VIRTUAL_IFACE_PREFIXES.any { name.startsWith(it, ignoreCase = true) }

@Composable
private fun NetworkCard(snap: MetricsSnapshot) {
    var showVirtual by remember { mutableStateOf(false) }
    val (virtual, real) = snap.network.partition { isVirtualIface(it.iface) }
    val shown = if (showVirtual) real + virtual else real

    PanelCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            SectionLabel("Network")
            if (virtual.isNotEmpty()) {
                TextButton(
                    onClick = { showVirtual = !showVirtual },
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
                ) {
                    Text(
                        if (showVirtual) "Hide virtual" else "+${virtual.size} VIRTUAL",
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }
        if (shown.isEmpty()) {
            MonoText("No active interfaces")
        }
        shown.forEach { n ->
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    n.iface,
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isVirtualIface(n.iface))
                        MaterialTheme.colorScheme.onSurfaceVariant
                    else MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                MonoText("↓ ${formatRate(n.rx_mb_s)}   ↑ ${formatRate(n.tx_mb_s)}")
            }
        }
    }
}
