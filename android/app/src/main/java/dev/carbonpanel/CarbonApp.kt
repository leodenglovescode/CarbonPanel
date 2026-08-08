package dev.carbonpanel

import android.app.Application
import dev.carbonpanel.widget.StatusWidgetWorker

class CarbonApp : Application() {
    override fun onCreate() {
        super.onCreate()
        StatusWidgetWorker.ensureScheduled(this)
    }
}
