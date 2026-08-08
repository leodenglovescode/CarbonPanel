package dev.carbonpanel.pairing

import com.journeyapps.barcodescanner.CaptureActivity
import com.journeyapps.barcodescanner.DecoratedBarcodeView
import dev.carbonpanel.R

/**
 * CaptureActivity with the app's own layout.
 *
 * CaptureActivity itself is kept — it owns the camera permission flow,
 * orientation handling and decode lifecycle, none of which is worth
 * reimplementing. Only the presentation is replaced, so pairing doesn't drop
 * the user into a screen that looks like a different application.
 *
 * The swap has to happen in initializeContent(), not onCreate(). onCreate()
 * calls initializeContent() and then hands the returned view to a
 * CaptureManager that opens the camera against it; calling setContentView()
 * after super.onCreate() leaves the manager driving a detached view, and the
 * screen stays black.
 */
class ScannerActivity : CaptureActivity() {
    override fun initializeContent(): DecoratedBarcodeView {
        setContentView(R.layout.activity_scanner)
        return findViewById(R.id.zxing_barcode_scanner)
    }
}
