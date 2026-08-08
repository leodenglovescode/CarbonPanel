plugins {
    // AGP 9 has built-in Kotlin support — applying org.jetbrains.kotlin.android
    // on top of it is now an error. See https://kotl.in/gradle/agp-built-in-kotlin
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
    alias(libs.plugins.kotlin.serialization) apply false
}
