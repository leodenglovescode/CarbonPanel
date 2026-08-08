package dev.carbonpanel.pairing

import android.os.Bundle
import com.journeyapps.barcodescanner.CaptureActivity
import dev.carbonpanel.R

/**
 * CaptureActivity with the app's own layout.
 *
 * CaptureActivity itself is kept — it owns the camera permission flow,
 * orientation handling and decode lifecycle, none of which is worth
 * reimplementing. Only the presentation is replaced, so pairing doesn't drop
 * the user into a screen that looks like a different application.
 */
class ScannerActivity : CaptureActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scanner)
    }
}
