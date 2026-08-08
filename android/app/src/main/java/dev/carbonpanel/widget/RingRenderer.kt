package dev.carbonpanel.widget

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import androidx.annotation.ColorInt

/**
 * Draws a ring gauge to a Bitmap.
 *
 * Glance widgets render as RemoteViews, which have no Canvas and no custom
 * views — so a ring cannot be drawn declaratively the way it can in the app.
 * Rendering to a Bitmap and handing Glance an ImageProvider is the only route
 * to a real gauge here; the alternative was a progress bar, which is what the
 * widget looked like before.
 */
object RingRenderer {

    /**
     * @param percent 0..100, always on that scale — a disk gauge that rescaled
     *   to its own max would make 40% full look alarming.
     * @param sizePx outer square size.
     * @param label short text drawn under the value inside the ring, or null.
     */
    fun draw(
        percent: Double,
        @ColorInt color: Int,
        @ColorInt trackColor: Int,
        @ColorInt textColor: Int,
        sizePx: Int,
        label: String? = null,
    ): Bitmap {
        val bmp = Bitmap.createBitmap(sizePx, sizePx, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bmp)

        val stroke = sizePx * 0.11f
        val inset = stroke / 2f + sizePx * 0.02f
        val bounds = RectF(inset, inset, sizePx - inset, sizePx - inset)

        val trackPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeWidth = stroke
            this.color = trackColor
            strokeCap = Paint.Cap.ROUND
        }
        val arcPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            style = Paint.Style.STROKE
            strokeWidth = stroke
            this.color = color
            strokeCap = Paint.Cap.ROUND
        }

        canvas.drawArc(bounds, 0f, 360f, false, trackPaint)

        val sweep = (percent.coerceIn(0.0, 100.0) / 100.0 * 360.0).toFloat()
        // Starts at 12 o'clock so a glance reads it like a dial.
        if (sweep > 0.5f) canvas.drawArc(bounds, -90f, sweep, false, arcPaint)

        val cx = sizePx / 2f
        val valueText = "${percent.coerceIn(0.0, 100.0).toInt()}%"

        val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            this.color = textColor
            textAlign = Paint.Align.CENTER
            typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
            textSize = if (label == null) sizePx * 0.30f else sizePx * 0.27f
        }
        // The value is at most "100%", so it fits the full inner width.
        shrinkToFit(valuePaint, valueText, sizePx * 0.66f, sizePx * 0.14f)

        val valueBaseline =
            if (label == null) cx - (valuePaint.descent() + valuePaint.ascent()) / 2f
            else cx - (valuePaint.descent() + valuePaint.ascent()) / 2f - sizePx * 0.06f
        canvas.drawText(valueText, cx, valueBaseline, valuePaint)

        if (label != null) {
            val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                this.color = textColor
                alpha = 165
                textAlign = Paint.Align.CENTER
                typeface = Typeface.MONOSPACE
                textSize = sizePx * 0.14f
            }
            // The sub-label sits below the centre, where the circle has already
            // narrowed — the usable chord there is about 0.63x the diameter, not
            // the full width. Sizing it as a fixed fraction of the ring is what
            // let strings like "1081/3666" spill past the stroke.
            shrinkToFit(labelPaint, label, sizePx * 0.58f, sizePx * 0.085f)
            canvas.drawText(label, cx, valueBaseline + sizePx * 0.19f, labelPaint)
        }

        return bmp
    }

    /**
     * Reduces [paint]'s text size until [text] fits [maxWidth], down to
     * [minTextSize].
     *
     * Callers can't know how long a mountpoint or a byte count will be, so the
     * fit has to be measured rather than assumed. Below the floor the text
     * would be unreadable anyway, and clipping is the better failure.
     */
    private fun shrinkToFit(paint: Paint, text: String, maxWidth: Float, minTextSize: Float) {
        var guard = 0
        while (paint.measureText(text) > maxWidth && paint.textSize > minTextSize && guard < 40) {
            paint.textSize -= maxOf(0.5f, paint.textSize * 0.06f)
            guard++
        }
    }
}
