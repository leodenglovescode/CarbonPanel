package dev.carbonpanel.ui.screens

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.Settings as AndroidSettings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import dev.carbonpanel.ui.components.LocalizedText as Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.journeyapps.barcodescanner.ScanContract
import com.journeyapps.barcodescanner.ScanOptions
import dev.carbonpanel.R
import dev.carbonpanel.pairing.PairState
import dev.carbonpanel.pairing.ScannerActivity
import dev.carbonpanel.pairing.PairingViewModel
import dev.carbonpanel.ui.components.ErrorBanner
import dev.carbonpanel.ui.components.InlineSpinner
import dev.carbonpanel.ui.components.MonoText
import dev.carbonpanel.ui.components.PanelCard

@Composable
fun PairingScreen(
    viewModel: PairingViewModel,
    onPaired: () -> Unit,
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showManual by rememberSaveable { mutableStateOf(false) }
    var manualUrl by rememberSaveable { mutableStateOf("") }
    var manualCode by rememberSaveable { mutableStateOf("") }
    var cameraDenied by rememberSaveable { mutableStateOf(false) }

    val scanLauncher = rememberLauncherForActivityResult(ScanContract()) { result ->
        result.contents?.let { viewModel.pairFromQr(it) }
    }

    fun launchScanner() {
        scanLauncher.launch(
            ScanOptions()
                .setCaptureActivity(ScannerActivity::class.java)
                .setDesiredBarcodeFormats(ScanOptions.QR_CODE)
                // Overrides the status line under the frame. The header on the
                // scanner layout already says where to find the code, so this
                // says what to do rather than repeating it.
                .setPrompt(context.getString(R.string.scan_camera_prompt))
                .setBeepEnabled(false)
                .setOrientationLocked(false)
        )
    }

    val cameraPermission = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        cameraDenied = !granted
        if (granted) launchScanner()
    }

    LaunchedEffect(state) {
        if (state is PairState.Paired) onPaired()
    }

    // Centred vertically when the content fits, scrollable when it doesn't.
    // A plain verticalScroll column measures against unbounded height, so
    // Arrangement.Center has nothing to centre within and everything piles up
    // at the top — which is what it was doing. Constraining the minimum height
    // to the viewport gives the arrangement something to work against.
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val viewportHeight = maxHeight

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = viewportHeight)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 32.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
        Viewfinder()

        Spacer(Modifier.height(28.dp))

        Text(
            "CarbonPanel",
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onBackground,
        )
        Spacer(Modifier.height(6.dp))
        Text(
            "Pair this phone with your server",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Spacer(Modifier.height(28.dp))

        // Numbered steps rather than a paragraph. Pairing spans two devices,
        // and "which screen am I meant to be on" is the whole difficulty.
        PanelCard(Modifier.fillMaxWidth(), spacing = 14) {
            Step(1, "Open the web panel", "On a computer, signed in as admin")
            Step(2, "Go to Settings", "Find the Paired Devices section")
            Step(3, "Scan the code", "Tap the button below and point your camera")
        }

        Spacer(Modifier.height(20.dp))

        when (val s = state) {
            is PairState.Working -> {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    modifier = Modifier.padding(vertical = 8.dp),
                ) {
                    InlineSpinner()
                    Text("Contacting server…", style = MaterialTheme.typography.bodySmall)
                }
            }
            is PairState.Failed -> {
                ErrorBanner(s.message)
                Spacer(Modifier.height(12.dp))
            }
            else -> Unit
        }

        if (cameraDenied) {
            ErrorBanner("Camera access is required to scan a pairing code.")
            TextButton(
                onClick = {
                    context.startActivity(
                        Intent(
                            AndroidSettings.ACTION_APPLICATION_DETAILS_SETTINGS,
                            Uri.parse("package:${context.packageName}"),
                        ),
                    )
                },
            ) {
                Text("Open app settings")
            }
            Spacer(Modifier.height(8.dp))
        }

        Button(
            onClick = {
                val granted = ContextCompat.checkSelfPermission(
                    context, Manifest.permission.CAMERA
                ) == PackageManager.PERMISSION_GRANTED
                cameraDenied = false
                if (granted) launchScanner() else cameraPermission.launch(Manifest.permission.CAMERA)
            },
            enabled = state !is PairState.Working,
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(vertical = 16.dp),
        ) {
            Icon(Icons.Filled.QrCodeScanner, contentDescription = null, modifier = Modifier.size(19.dp))
            Spacer(Modifier.width(10.dp))
            Text("Scan pairing code", fontWeight = FontWeight.Medium)
        }

        Spacer(Modifier.height(10.dp))

        OutlinedButton(
            onClick = { showManual = !showManual },
            modifier = Modifier.fillMaxWidth(),
            contentPadding = PaddingValues(vertical = 13.dp),
        ) {
            Text(if (showManual) "Hide manual entry" else "Enter code manually")
        }

        AnimatedVisibility(visible = showManual) {
            PanelCard(Modifier.fillMaxWidth().padding(top = 12.dp), spacing = 10) {
                MonoText(
                    "For a publicly trusted HTTPS server. Self-signed certificates " +
                        "must be paired by scanning the QR so the certificate pin is included.",
                )
                OutlinedTextField(
                    value = manualUrl,
                    onValueChange = { manualUrl = it },
                    label = { Text("Server address") },
                    placeholder = { Text("https://panel.example.com") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = manualCode,
                    onValueChange = { manualCode = it.uppercase() },
                    label = { Text("Pairing code") },
                    placeholder = { Text("MKK3H5JCT9QW") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        capitalization = KeyboardCapitalization.Characters,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = { viewModel.pairManually(manualUrl, manualCode) },
                    enabled = manualUrl.isNotBlank() && manualCode.isNotBlank() &&
                        state !is PairState.Working,
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Pair") }
            }
        }

        Spacer(Modifier.height(24.dp))

        // Says plainly what pairing does. Handing a phone credentials to a
        // server is the kind of thing worth being unambiguous about.
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.Top,
        ) {
            Box(
                Modifier
                    .padding(top = 5.dp)
                    .size(5.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primary),
            )
            MonoText(
                "No password or 2FA code is typed on this phone. Pairing grants " +
                    "a token you can revoke from the panel at any time.",
            )
        }

        Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun Step(number: Int, title: String, detail: String) {
    Row(
        verticalAlignment = Alignment.Top,
        horizontalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Box(
            Modifier
                .size(24.dp)
                .clip(CircleShape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                "$number",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold,
            )
        }
        Column {
            Text(title, style = MaterialTheme.typography.bodyMedium)
            MonoText(detail)
        }
    }
}

/**
 * Animated QR viewfinder.
 *
 * Corner brackets plus a sweeping scan line — the visual language of "point
 * your camera at something", which is exactly the action being asked for. The
 * screen was otherwise three lines of text on an empty background, giving no
 * clue that a camera was involved.
 */
@Composable
private fun Viewfinder() {
    val accent = MaterialTheme.colorScheme.primary
    val dim = MaterialTheme.colorScheme.outline

    val transition = rememberInfiniteTransition(label = "viewfinder")
    val sweep by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(2200, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "sweep",
    )

    Canvas(Modifier.size(132.dp)) {
        val w = size.width
        val h = size.height
        val stroke = 3.dp.toPx()
        val arm = w * 0.26f      // bracket arm length
        val r = 4.dp.toPx()

        // Four corner brackets.
        listOf(
            Offset(0f, 0f) to Pair(1f, 1f),
            Offset(w, 0f) to Pair(-1f, 1f),
            Offset(0f, h) to Pair(1f, -1f),
            Offset(w, h) to Pair(-1f, -1f),
        ).forEach { (corner, dir) ->
            val (dx, dy) = dir
            drawLine(
                accent, corner + Offset(0f, dy * r), corner + Offset(0f, dy * arm),
                strokeWidth = stroke, cap = androidx.compose.ui.graphics.StrokeCap.Round,
            )
            drawLine(
                accent, corner + Offset(dx * r, 0f), corner + Offset(dx * arm, 0f),
                strokeWidth = stroke, cap = androidx.compose.ui.graphics.StrokeCap.Round,
            )
        }

        // Three finder squares, the part of a QR everyone recognises.
        val fs = w * 0.19f
        val inset = w * 0.20f
        listOf(
            Offset(inset, inset),
            Offset(w - inset - fs, inset),
            Offset(inset, h - inset - fs),
        ).forEach { p ->
            drawRoundRect(
                color = dim,
                topLeft = p,
                size = Size(fs, fs),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(2.dp.toPx()),
                style = Stroke(width = 2.dp.toPx()),
            )
            drawRoundRect(
                color = dim,
                topLeft = p + Offset(fs * 0.3f, fs * 0.3f),
                size = Size(fs * 0.4f, fs * 0.4f),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(1.dp.toPx()),
            )
        }

        // Scan line, fading out at both edges so it reads as a beam.
        val y = h * (0.18f + 0.64f * sweep)
        drawLine(
            brush = Brush.horizontalGradient(
                0f to Color.Transparent,
                0.5f to accent,
                1f to Color.Transparent,
            ),
            start = Offset(w * 0.1f, y),
            end = Offset(w * 0.9f, y),
            strokeWidth = 2.dp.toPx(),
        )
    }
}
