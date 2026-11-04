package dev.carbonpanel.pairing

import java.net.ConnectException
import java.net.SocketTimeoutException
import java.security.cert.CertificateException
import javax.net.ssl.SSLHandshakeException
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.*
import org.junit.Test
import retrofit2.HttpException
import retrofit2.Response

class PairingErrorsTest {
    @Test fun untrustedCertificateExplainsQrAndServerPermissions() {
        val error = SSLHandshakeException("untrusted").apply {
            initCause(CertificateException("Trust anchor not found"))
        }
        val message = pairingError(error)
        assertTrue(message.contains("QR"))
        assertTrue(message.contains("permissions"))
    }

    @Test fun pinMismatchRequiresNewQr() {
        val error = SSLHandshakeException("TLS").apply {
            initCause(CertificateException("Certificate does not match the fingerprint in the pairing code."))
        }
        assertTrue(pairingError(error).contains("does not match the QR"))
    }

    @Test fun rateLimitIsNotReportedAsUnreachable() {
        val error = HttpException(Response.error<Unit>(429, "".toResponseBody()))
        assertTrue(pairingError(error).contains("Too many pairing attempts"))
    }

    @Test fun invalidCodeExplainsInputProblem() {
        val error = HttpException(Response.error<Unit>(422, "".toResponseBody()))
        assertTrue(pairingError(error).contains("Invalid pairing code format"))
    }

    @Test fun transportFailuresRemainDistinct() {
        assertEquals("Connection timed out.", pairingError(SocketTimeoutException()))
        assertEquals("Connection refused or server unreachable.", pairingError(ConnectException()))
    }

    @Test fun unknownErrorsDoNotExposePotentiallySensitiveMessages() {
        assertFalse(pairingError(IllegalStateException("secret-code")).contains("secret-code"))
    }
}
