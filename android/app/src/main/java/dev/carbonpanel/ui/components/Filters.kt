package dev.carbonpanel.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.unit.dp

/**
 * Search field for the list screens.
 *
 * A server with dozens of containers and hundreds of systemd units is not
 * navigable by scrolling, which is the whole reason this exists.
 */
@Composable
fun SearchField(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        placeholder = {
            Text(placeholder, style = MaterialTheme.typography.bodySmall)
        },
        leadingIcon = {
            Icon(
                Icons.Filled.Search,
                contentDescription = null,
                modifier = Modifier.size(17.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        },
        trailingIcon = {
            if (value.isNotEmpty()) {
                IconButton(onClick = { onValueChange("") }) {
                    Icon(
                        Icons.Filled.Close,
                        contentDescription = "Clear",
                        modifier = Modifier.size(17.dp),
                    )
                }
            }
        },
        singleLine = true,
        textStyle = TextStyle(
            fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
            fontSize = MaterialTheme.typography.bodyMedium.fontSize,
            color = MaterialTheme.colorScheme.onSurface,
        ),
        modifier = modifier.fillMaxWidth(),
    )
}

/**
 * Wrapping variant, for option sets whose length isn't known up front —
 * mountpoints and interface names are arbitrary strings and routinely overflow
 * a single row, where a non-wrapping Row would silently clip them.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun <T> SegmentedFilterWrapped(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier,
) {
    FlowRow(
        modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        options.forEach { option ->
            androidx.compose.material3.FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = {
                    Text(
                        label(option),
                        style = MaterialTheme.typography.labelMedium,
                        maxLines = 1,
                    )
                },
            )
        }
    }
}

/** Segmented row of mutually exclusive filters. */
@Composable
fun <T> SegmentedFilter(
    options: List<T>,
    selected: T,
    label: (T) -> String,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        options.forEach { option ->
            androidx.compose.material3.FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = {
                    Text(label(option), style = MaterialTheme.typography.labelMedium)
                },
            )
        }
    }
}

// ── storage filtering ──────────────────────────────────────────────────────
//
// The /disks endpoint flags squashfs and loop devices as virtual, but the
// metrics snapshot's disk list carries no such flag — psutil's
// disk_partitions(all=False) still reports every snap mount, because each one
// is a genuine mount of a real loop device. On a desktop-derived install that
// is 20+ entries burying the disks that matter, so the app filters by
// mountpoint and device shape instead of trusting a flag that isn't there.

private val PSEUDO_MOUNT_PREFIXES = listOf(
    "/snap/",
    "/var/lib/docker",
    "/var/lib/containers",
    "/var/lib/snapd",
    "/run/",
    "/sys/",
    "/proc/",
    "/dev/",
    "/boot/efi",
)

private val PSEUDO_FSTYPES = setOf(
    "squashfs", "overlay", "overlay2", "tmpfs", "devtmpfs", "ramfs",
    "aufs", "efivarfs", "nsfs", "autofs", "fuse.portal", "fuseblk.snap",
)

/** True for mounts a human would not call "a disk". */
fun isPseudoMount(mountpoint: String, device: String = "", fstype: String = ""): Boolean {
    if (fstype.lowercase() in PSEUDO_FSTYPES) return true
    if (device.removePrefix("/dev/").startsWith("loop")) return true
    if (PSEUDO_MOUNT_PREFIXES.any { mountpoint.startsWith(it, ignoreCase = true) }) return true
    return false
}
