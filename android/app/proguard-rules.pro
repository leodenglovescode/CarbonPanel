# kotlinx.serialization keeps its generated serializers on the companion.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class dev.carbonpanel.data.** {
    *** Companion;
}
-keepclasseswithmembers class dev.carbonpanel.data.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# OkHttp / Retrofit
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn retrofit2.**
-keepattributes Signature, Exceptions

# Tink, pulled in by androidx.security:security-crypto for the encrypted
# token store, is annotated with Error Prone annotations that are
# compile-time only and absent at runtime. R8 treats the dangling references
# as errors and fails the release build outright, so they are explicitly
# ignored — nothing reads these annotations on device.
-dontwarn com.google.errorprone.annotations.**

# Retrofit builds its API implementation from generic return types, which R8
# will otherwise erase; without these the release build compiles and then
# fails at runtime on the first call, which is the worst kind of breakage.
-keepattributes RuntimeVisibleAnnotations, RuntimeVisibleParameterAnnotations
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation

# Room generates *_Impl subclasses that are constructed reflectively, so R8
# cannot see the no-arg constructor being used and strips it. WorkManager's
# WorkDatabase_Impl is one of these, and losing it crashed the release build
# on launch with NoSuchMethodException before androidx.startup could finish:
#   RuntimeException: Unable to get provider androidx.startup.InitializationProvider
-keep class * extends androidx.room.RoomDatabase { <init>(); }
-dontwarn androidx.room.paging.**

# androidx.startup discovers initializers by class name from the manifest, and
# WorkManager instantiates Workers reflectively — both are invisible to R8.
-keep class * implements androidx.startup.Initializer { <init>(); }
-keep class * extends androidx.work.ListenableWorker { <init>(...); }
