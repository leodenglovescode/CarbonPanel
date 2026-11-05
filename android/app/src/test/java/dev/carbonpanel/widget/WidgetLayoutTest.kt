package dev.carbonpanel.widget

import androidx.compose.ui.unit.dp
import org.junit.Assert.*
import org.junit.Test

class WidgetLayoutTest {
    @Test fun contentFitsAcrossResizeAndAccessibilitySizes() {
        for (width in listOf(140, 180, 320, 420, 640)) {
            for (height in listOf(70, 90, 96, 120, 132, 160, 190, 220, 320)) {
                for (fontScale in listOf(1f, 1.3f, 1.5f, 2f)) {
                    for (gpu in listOf(false, true)) {
                        for (stale in listOf(false, true)) {
                            val layout = widgetLayout(width.dp, height.dp, gpu, 3f, fontScale, stale)
                            assertTrue("${width}x$height font=$fontScale gpu=$gpu stale=$stale: $layout",
                                layout.requiredHeight <= height.dp)
                            assertTrue(layout.ring > 0.dp)
                            assertTrue(layout.ringPx <= 160)
                        }
                    }
                }
            }
        }
    }

    @Test fun shortWideWidgetShrinksRingsToKeepNetworkFullyVisible() {
        val layout = widgetLayout(420.dp, 220.dp, false, 3f, 1f, false)
        assertTrue(layout.showHeader)
        assertTrue(layout.showNetwork)
        assertTrue(layout.ring < 104.dp)
        assertTrue(layout.requiredHeight <= 220.dp)
    }

    @Test fun staleMessageAndLargerTextGetTheirOwnHeightBudget() {
        val normal = widgetLayout(420.dp, 220.dp, false, 3f, 1f, false)
        val stale = widgetLayout(420.dp, 220.dp, false, 3f, 1f, true)
        val largeText = widgetLayout(420.dp, 220.dp, false, 3f, 1.5f, true)
        assertTrue(stale.showStale)
        assertTrue(stale.ring < normal.ring)
        assertTrue(largeText.ring < stale.ring)
    }

    @Test fun SmallestWidgetsDropSecondaryRows() {
        val layout = widgetLayout(140.dp, 70.dp, true, 3f, 2f, true)
        assertFalse(layout.showHeader)
        assertFalse(layout.showNetwork)
        assertFalse(layout.showStale)
    }
}
