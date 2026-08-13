package dev.carbonpanel.pairing

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import com.journeyapps.barcodescanner.ViewfinderView

/**
 * Viewfinder matching the rest of the app.
 *
 * ZXing's stock view draws a red laser line across a plain rectangle, which
 * looks nothing like the panel and reads as a debug overlay. This replaces it
 * with a dimmed surround and accent corner brackets — the same shape used on
 * the pairing screen, so the two read as one flow.
 */
class CarbonViewfinderView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : ViewfinderView(context, attrs) {

    private val scrim = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(160, 0, 0, 0)
    }
    private val bracket = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = ACCENT
        style = Paint.Style.STROKE
        strokeWidth = 6f
        strokeCap = Paint.Cap.ROUND
    }
    private val hairline = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(70, 0, 255, 136)
        style = Paint.Style.STROKE
        strokeWidth = 2f
    }
    private val drawFrame = RectF()

    override fun onDraw(canvas: Canvas) {
        refreshSizes()
        val frame = framingRect
        if (frame == null) {
            // The rect isn't known until the camera reports its preview size,
            // so keep checking rather than staying blank forever.
            postInvalidateDelayed(REDRAW_DELAY_MS)
            return
        }

        val w = width.toFloat()
        val h = height.toFloat()
        drawFrame.set(frame)
        val f = drawFrame
        val radius = 20f

        // Dim everything outside the framing rect so the eye lands on the
        // window rather than the whole camera feed.
        canvas.save()
        canvas.clipOutRect(f)
        canvas.drawRect(0f, 0f, w, h, scrim)
        canvas.restore()

        canvas.drawRoundRect(f, radius, radius, hairline)

        // Corner brackets, one per corner, drawn without allocating
        // temporary collections during every camera frame.
        val arm = minOf(f.width(), f.height()) * 0.16f
        drawCorner(canvas, f.left, f.top, 1f, 1f, arm)
        drawCorner(canvas, f.right, f.top, -1f, 1f, arm)
        drawCorner(canvas, f.left, f.bottom, 1f, -1f, arm)
        drawCorner(canvas, f.right, f.bottom, -1f, -1f, arm)

        // Deliberately no laser line and no animation: a QR decodes the
        // instant it's in frame, so a sweeping beam implies progress that
        // isn't happening. The one redraw below tracks a framing rect that can
        // move when the camera reconfigures; it is not an animation loop.
        postInvalidateDelayed(TRACK_DELAY_MS)
    }

    private fun drawCorner(
        canvas: Canvas,
        x: Float,
        y: Float,
        dx: Float,
        dy: Float,
        arm: Float,
    ) {
        canvas.drawLine(x, y + dy * 2, x, y + dy * arm, bracket)
        canvas.drawLine(x + dx * 2, y, x + dx * arm, y, bracket)
    }

    private companion object {
        const val ACCENT = 0xFF00FF88.toInt()
        const val REDRAW_DELAY_MS = 120L
        const val TRACK_DELAY_MS = 400L
    }
}
