package dev.carbonpanel.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import java.io.File

/** Device-wide appearance file. Never passed to the API or stored with a server. */
object ChooserBackground {
    private fun directory(context: Context) = File(context.filesDir, "appearance").apply { mkdirs() }
    fun file(context: Context) = File(directory(context), "server-chooser.jpg")
    fun version(context: Context): Long = file(context).let { if (it.isFile) it.lastModified() else 0L }
    fun remove(context: Context) {
        val photo = file(context)
        check(!photo.exists() || photo.delete()) { "Could not remove the local photo" }
    }

    /** Copy into internal storage so a revoked photo-picker grant cannot lose the image. */
    fun save(context: Context, uri: Uri) {
        val source = File.createTempFile("chooser-source-", ".image", directory(context))
        val output = File.createTempFile("chooser-crop-", ".jpg", directory(context))
        var bitmap: Bitmap? = null
        try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                source.outputStream().use { destination ->
                    val buffer = ByteArray(64 * 1024)
                    var total = 0
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        total += count
                        require(total <= 20 * 1024 * 1024) { "Please choose a photo smaller than 20 MB" }
                        destination.write(buffer, 0, count)
                    }
                }
            } ?: error("This photo could not be opened")
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeFile(source.path, bounds)
            require(bounds.outWidth > 0 && bounds.outHeight > 0 && bounds.outWidth.toLong() * bounds.outHeight <= 40_000_000) { "Please choose an image smaller than 40 megapixels" }
            var sample = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 2560) sample *= 2
            val decoded = BitmapFactory.decodeFile(source.path, BitmapFactory.Options().apply { inSampleSize = sample }) ?: error("Unsupported image")
            bitmap = decoded
            val orientation = ExifInterface(source.path).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            val matrix = Matrix().apply {
                when (orientation) {
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> setScale(-1f, 1f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> setRotate(180f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> setScale(1f, -1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> { setRotate(90f); postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_90 -> setRotate(90f)
                    ExifInterface.ORIENTATION_TRANSVERSE -> { setRotate(-90f); postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_270 -> setRotate(-90f)
                }
            }
            if (!matrix.isIdentity) {
                bitmap = Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true)
                if (bitmap !== decoded) decoded.recycle()
            }
            output.outputStream().use { check(requireNotNull(bitmap).compress(Bitmap.CompressFormat.JPEG, 88, it)) { "Could not save the photo" } }
            check(output.renameTo(file(context))) { "Could not store the photo on this phone" }
        } finally {
            bitmap?.recycle()
            source.delete(); output.delete()
        }
    }
}
