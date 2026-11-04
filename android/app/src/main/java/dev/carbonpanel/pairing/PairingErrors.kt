package dev.carbonpanel.pairing

import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.security.cert.CertificateException
import javax.net.ssl.SSLException
import javax.net.ssl.SSLPeerUnverifiedException
import retrofit2.HttpException

/** User-facing failures never include pairing codes, request bodies, or tokens. */
internal fun pairingError(error: Throwable): String {
    val causes = generateSequence(error) { it.cause }.take(12).toList()
    val http = causes.filterIsInstance<HttpException>().firstOrNull()
    if (http != null) return when (http.code()) {
        400 -> "Pairing code was used or expired. Generate a new one."
        422 -> "Invalid pairing code format. Check the code or scan a new QR."
        429 -> "Too many pairing attempts. Wait a few minutes before trying again."
        404 -> "Pairing API not found. Check the address and update the server."
        else -> "Server returned HTTP ${http.code()} while pairing."
    }
    if (causes.any { it is CertificateException || it is SSLException }) {
        if (causes.any { it.message?.contains("fingerprint in the pairing code") == true }) {
            return "Certificate does not match the QR. Generate a new QR from the server."
        }
        if (causes.any { it is SSLPeerUnverifiedException }) {
            return "Certificate does not identify this address. Use an address listed in the certificate."
        }
        return "TLS certificate could not be verified. Self-signed servers require a QR with " +
            "the certificate fingerprint. Check the server's TLS certificate configuration and permissions."
    }
    return when {
        causes.any { it is SocketTimeoutException } -> "Connection timed out."
        causes.any { it is UnknownHostException } -> "Server hostname could not be resolved."
        causes.any { it is ConnectException } -> "Connection refused or server unreachable."
        else -> "Pairing request failed (${error.javaClass.simpleName})."
    }
}
