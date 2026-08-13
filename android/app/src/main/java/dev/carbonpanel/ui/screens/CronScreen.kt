package dev.carbonpanel.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dev.carbonpanel.data.CronJob
import dev.carbonpanel.ui.Load
import dev.carbonpanel.ui.PanelViewModel
import dev.carbonpanel.ui.components.*
import dev.carbonpanel.ui.theme.Danger

@Composable
fun CronScreen(viewModel: PanelViewModel) {
    val managed by viewModel.managedCron.collectAsStateWithLifecycle()
    val entries by viewModel.cronEntries.collectAsStateWithLifecycle()
    val busy by viewModel.busy.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { viewModel.loadCron() }

    var editing by remember { mutableStateOf<CronJob?>(null) }
    var creating by remember { mutableStateOf(false) }
    var deleting by remember { mutableStateOf<CronJob?>(null) }

    if (creating || editing != null) {
        CronEditor(
            job = editing,
            saving = "cron" in busy,
            onSave = { label, schedule, command ->
                viewModel.saveCron(editing?.id, label, schedule, command)
                creating = false; editing = null
            },
            onDismiss = { creating = false; editing = null },
        )
    }

    deleting?.let { job ->
        ConfirmDialog(
            title = "Delete job",
            body = "Delete \"${job.label.ifBlank { job.command }}\"? This removes it from the crontab.",
            confirmLabel = "Delete",
            onConfirm = { viewModel.deleteCron(job.id) },
            onDismiss = { deleting = null },
        )
    }

    LoadList(
        state = managed,
        onRefresh = { viewModel.loadCron(refresh = true) },
        emptyTitle = "No managed jobs",
        emptyDetail = "Jobs created here are written to the crontab and can be edited later.",
        header = {
            item {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    SectionLabel("Managed by carbonpanel")
                    TextButton(onClick = { creating = true }) { Text("New job") }
                }
            }
        },
    ) { jobs ->
        items(jobs, key = { it.id }) { job ->
            PanelCard(Modifier.fillMaxWidth()) {
                Text(
                    job.label.ifBlank { "(unlabelled)" },
                    style = MaterialTheme.typography.bodyMedium,
                )
                MonoText(job.schedule)
                MonoText(job.command, maxLines = 3)
                Row(
                    horizontalArrangement = Arrangement.spacedBy(2.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    if (job.id in busy) {
                        InlineSpinner()
                    } else {
                        TextButton(onClick = { editing = job }) { Text("Edit") }
                        TextButton(onClick = { deleting = job }) { Text("Delete", color = Danger) }
                    }
                }
            }
        }

        // Everything else in the system crontabs, read-only — the panel didn't
        // write these and shouldn't imply it can safely rewrite them.
        val system = (entries as? Load.Ok)?.data.orEmpty()
        if (system.isNotEmpty()) {
            item { SectionLabel("System crontab · read-only") }
            items(system.size) { i ->
                val e = system[i]
                PanelCard(Modifier.fillMaxWidth()) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        MonoText(e.schedule)
                        MonoText("${e.user}@${e.source}")
                    }
                    Text(
                        e.command,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = 3,
                    )
                }
            }
        }
    }
}

@Composable
private fun CronEditor(
    job: CronJob?,
    saving: Boolean,
    onSave: (String, String, String) -> Unit,
    onDismiss: () -> Unit,
) {
    var label by remember { mutableStateOf(job?.label ?: "") }
    var schedule by remember { mutableStateOf(job?.schedule ?: "0 * * * *") }
    var command by remember { mutableStateOf(job?.command ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (job == null) "New cron job" else "Edit job",
                style = MaterialTheme.typography.titleMedium,
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    value = label,
                    onValueChange = { label = it },
                    label = { Text("Label") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = schedule,
                    onValueChange = { schedule = it },
                    label = { Text("Schedule") },
                    supportingText = { Text("min hour dom month dow — e.g. 0 3 * * *") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = command,
                    onValueChange = { command = it },
                    label = { Text("Command") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onSave(label, schedule.trim(), command.trim()) },
                enabled = !saving && schedule.isNotBlank() && command.isNotBlank(),
            ) { Text(if (saving) "Saving…" else "Save") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
        containerColor = MaterialTheme.colorScheme.surface,
    )
}
