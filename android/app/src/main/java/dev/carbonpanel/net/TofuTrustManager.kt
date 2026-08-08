package dev.carbonpanel.net

import dev.carbonpanel.data.Prefs
import java.net.Socket
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.SSLEngine
import javax.net.ssl.TrustManagerFactory
import javax.net.ssl.X509ExtendedTrustManager

/**
 * Trust manager that accepts a self-signed certificate pinned on first use.
 *
 * Self-hosted panels overwhelmingly run either plain HTTP on a private network
 * or HTTPS with a self-signed certificate. Android rejects the latter outright,
 * and that is not a hypothetical problem for this codebase: migration 0011
 * removed passkey support precisely because platform authenticators refuse to
 * run on an untrusted certificate. Rejecting self-signed certs here would make
 * the app unusable for most of its intended users.
 *
 * The policy, in order:
 *
 *  1. If the chain validates against the system CA store, accept it and pin
 *     nothing. Real certificates keep their real guarantees, including
 *     revocation and expiry.
 *  2. Otherwise, if a fingerprint is already pinned for this host, require an
 *     exact match. A changed self-signed certificate is a hard failure, not a
 *     prompt — that is the case worth being loud about.
 *  3. Otherwise, record the fingerprint and accept (trust on first use).
 *
 * Step 3 is the weak point and it is deliberate: the first connection is
 * unauthenticated. It happens during pairing, seconds after the user scanned a
 * QR code off their own screen, usually on their own network. Every subsequent
 * connection is pinned. This is the same bargain SSH makes, and unlike a blanket
 * "trust all certificates" trust manager it detects interception from that point
 * on.
 */
class TofuTrustManager(
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
        val host = (socket?.inetAddress?.hostName) ?: socket?.inetAddress?.hostAddress
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

        try {
            systemCheck()
            return  // Publicly trusted — nothing to pin.
        } catch (systemFailure: CertificateException) {
            // Fall through to the pinning path. The host is required for that;
            // without it we cannot scope a pin and must not accept blindly.
            val key = host?.lowercase()
                ?: throw CertificateException(
                    "Untrusted certificate and no host to pin it against", systemFailure,
                )

            val fingerprint = sha256(chain[0])
            val pinned = prefs.pinnedCert(key)

            when {
                pinned == null -> {
                    // Trust on first use — see the class comment for why this
                    // is acceptable here and where its limits are.
                    prefs.setPinnedCert(key, fingerprint)
                }

                pinned.equals(fingerprint, ignoreCase = true) -> {
                    // Same certificate as the one seen at pairing time.
                }

                else -> throw CertificateException(
                    "Certificate for $key changed. Expected $pinned but got $fingerprint. " +
                        "If you genuinely replaced the server's certificate, re-pair the device; " +
                        "otherwise this connection is being intercepted.",
                    systemFailure,
                )
            }
        }
    }

    companion object {
        fun sha256(cert: X509Certificate): String =
            MessageDigest.getInstance("SHA-256")
                .digest(cert.encoded)
                .joinToString(":") { "%02X".format(it) }
    }
}
