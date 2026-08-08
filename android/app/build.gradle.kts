plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

android {
    namespace = "dev.carbonpanel"
    compileSdk = 36
    // Pinned to a revision that's actually installed. AGP would otherwise ask
    // for 36.0.0 and try to download it, which needs working access to
    // dl.google.com from the build machine.
    buildToolsVersion = "36.1.0"

    defaultConfig {
        applicationId = "dev.carbonpanel"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0.0"
    }

    // Release signing comes from the environment so CI can inject a keystore
    // without it ever being committed. Everything is optional: with nothing
    // set, the release build falls back to the debug key below.
    val keystorePath: String? = System.getenv("KEYSTORE_FILE")

    signingConfigs {
        create("release") {
            if (!keystorePath.isNullOrBlank()) {
                storeFile = file(keystorePath)
                storePassword = System.getenv("KEYSTORE_PASSWORD")
                keyAlias = System.getenv("KEY_ALIAS")
                keyPassword = System.getenv("KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            // A release APK signed with the debug key is still installable,
            // which is what matters for a sideloaded self-hosted app. An
            // *unsigned* release APK — AGP's default without a signing config —
            // cannot be installed at all and would make the CI artifact
            // useless. Set the KEYSTORE_* secrets to sign properly; note that
            // switching signing key later requires users to uninstall first.
            signingConfig = if (!keystorePath.isNullOrBlank()) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        debug {
            applicationIdSuffix = ".debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
    }

    lint {
        // lintVital runs as part of assembleRelease and resolves an extra
        // classpath of -jvmstubs/-desktop artifact variants, which is both slow
        // and a hard failure on networks that can't reach dl.google.com. Lint
        // is still available on demand via `./gradlew :app:lint`; it just no
        // longer stands between a green build and a shippable APK.
        checkReleaseBuilds = false
        abortOnError = false
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons)
    implementation(libs.androidx.navigation.compose)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.kotlinx.serialization.json)

    implementation(libs.androidx.security.crypto)
    implementation(libs.androidx.datastore.preferences)

    // QR scanning. ZXing rather than ML Kit Barcode: ML Kit pulls in Google
    // Play Services, which a meaningful share of self-hosters don't have
    // (GrapheneOS / LineageOS without gapps). ZXing is self-contained.
    implementation(libs.zxing.embedded)

    // Image loading for the panel background, which is served behind auth and
    // often over a self-signed cert — so it reuses ApiClient's OkHttp instance.
    implementation(libs.coil.compose)

    implementation(libs.androidx.glance.appwidget)
    implementation(libs.androidx.glance.material3)
    implementation(libs.androidx.work.runtime.ktx)
}
