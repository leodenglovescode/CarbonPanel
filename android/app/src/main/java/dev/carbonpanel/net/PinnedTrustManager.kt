package dev.carbonpanel.net

import android.annotation.SuppressLint
import dev.carbonpanel.data.Prefs
import java.net.Socket
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.SSLEngine
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509ExtendedTrustManager

/**
 * Trust manager for QR-bound self-signed certificates.
 *
 * A pin carried in the QR is installed before the first network request, so an
 * on-path attacker cannot win a trust-on-first-use race. Hosts without a QR pin
 * must validate normally against Android's system CA store.
 */
@SuppressLint("CustomX509TrustManager")
class PinnedTrustManager(
    private val prefs: Prefs,
) : X509ExtendedTrustManager() {

    private val systemTrustManager: X509ExtendedTrustManager = run {
        val factory = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm())
        factory.init(null as java.security.KeyStore?)
        factory.trustManagers
            .filterIsInstance<X509ExtendedTrustManager>()
            .firstOrNull()
            ?: error("No system X509ExtendedTrustManager available")
    }

    override fun getAcceptedIssuers(): Array<X509Certificate> =
        systemTrustManager.acceptedIssuers

    // Client certificates are never used by this app; defer wholesale.
    override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String) =
        systemTrustManager.checkClientTrusted(chain, authType)

    override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String, socket: Socket?) =
        systemTrustManager.checkClientTrusted(chain, authType, socket)

    override fun checkClientTrusted(chain: Array<X509Certificate>, authType: String, engine: SSLEngine?) =
        systemTrustManager.checkClientTrusted(chain, authType, engine)

    override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {
        verify(chain, authType, host = null) {
            systemTrustManager.checkServerTrusted(chain, authType)
        }
    }

    override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String, socket: Socket?) {
        val host = (socket as? javax.net.ssl.SSLSocket)
            ?.handshakeSession?.peerHost
            ?: socket?.inetAddress?.hostName
        verify(chain, authType, host) {
            systemTrustManager.checkServerTrusted(chain, authType, socket)
        }
    }

    override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String, engine: SSLEngine?) {
        verify(chain, authType, engine?.peerHost) {
            systemTrustManager.checkServerTrusted(chain, authType, engine)
        }
    }

    private inline fun verify(
        chain: Array<X509Certificate>,
        @Suppress("UNUSED_PARAMETER") authType: String,
        host: String?,
        systemCheck: () -> Unit,
    ) {
        if (chain.isEmpty()) throw CertificateException("Empty certificate chain")

        val key = host?.lowercase()
        val pinned = key?.let(prefs::pinnedCert)
        if (pinned != null) {
            chain[0].checkValidity()
            val fingerprint = sha256(chain[0])
            val normalizedPin = pinned.replace(":", "")
            val normalizedFingerprint = fingerprint.replace(":", "")
            if (!normalizedPin.equals(normalizedFingerprint, ignoreCase = true)) {
                throw CertificateException(
                    "Certificate for $key does not match the fingerprint in the pairing code. " +
                        "Expected $pinned but got $fingerprint.",
                )
            }
            return
        }

        // No out-of-band pin exists: only a normal publicly trusted chain is
        // acceptable. Self-signed certificates must be paired by scanning QR.
        systemCheck()
    }

    companion object {
        fun sha256(cert: X509Certificate): String =
            MessageDigest.getInstance("SHA-256")
                .digest(cert.encoded)
                .joinToString(":") { "%02X".format(it) }
    }
}
