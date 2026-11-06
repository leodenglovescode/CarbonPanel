function base64urlToBuffer(value: string): ArrayBuffer {
  const padded = value.replace(/-/g, '+').replace(/_/g, '/').padEnd(
    value.length + ((4 - (value.length % 4)) % 4),
    '=',
  )
  const binary = atob(padded)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  return bytes.buffer
}

function bufferToBase64url(value: ArrayBuffer): string {
  const bytes = new Uint8Array(value)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function isIpAddress(hostname: string): boolean {
  if (hostname.includes(':')) return true
  const parts = hostname.split('.')
  return parts.length === 4 && parts.every((part) => {
    if (!/^\d+$/.test(part)) return false
    const value = Number(part)
    return value >= 0 && value <= 255
  })
}

export function passkeyAvailability(): { available: boolean; reason: string } {
  if (
    !window.isSecureContext ||
    typeof window.PublicKeyCredential === 'undefined' ||
    !navigator.credentials
  ) {
    return {
      available: false,
      reason: 'Passkeys require a certificate trusted by this browser.',
    }
  }
  if (isIpAddress(window.location.hostname)) {
    return {
      available: false,
      reason: 'Passkeys require a stable domain hostname; IP addresses are not supported.',
    }
  }
  return { available: true, reason: '' }
}

function creationOptions(options: Record<string, any>): PublicKeyCredentialCreationOptions {
  return {
    ...options,
    challenge: base64urlToBuffer(options.challenge),
    user: {
      ...options.user,
      id: base64urlToBuffer(options.user.id),
    },
    excludeCredentials: (options.excludeCredentials || []).map((credential: any) => ({
      ...credential,
      id: base64urlToBuffer(credential.id),
    })),
  }
}

function requestOptions(options: Record<string, any>): PublicKeyCredentialRequestOptions {
  return {
    ...options,
    challenge: base64urlToBuffer(options.challenge),
    allowCredentials: options.allowCredentials?.map((credential: any) => ({
      ...credential,
      id: base64urlToBuffer(credential.id),
    })),
  }
}

export async function createPasskey(options: Record<string, any>): Promise<Record<string, any>> {
  const availability = passkeyAvailability()
  if (!availability.available) throw new Error(availability.reason)

  const credential = await navigator.credentials.create({
    publicKey: creationOptions(options),
  }) as PublicKeyCredential | null
  if (!credential) throw new Error('Passkey registration was cancelled.')

  const response = credential.response as AuthenticatorAttestationResponse
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment,
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      attestationObject: bufferToBase64url(response.attestationObject),
      transports: typeof response.getTransports === 'function' ? response.getTransports() : [],
    },
  }
}

export async function getPasskey(options: Record<string, any>): Promise<Record<string, any>> {
  const availability = passkeyAvailability()
  if (!availability.available) throw new Error(availability.reason)

  const credential = await navigator.credentials.get({
    publicKey: requestOptions(options),
  }) as PublicKeyCredential | null
  if (!credential) throw new Error('Passkey sign-in was cancelled.')

  const response = credential.response as AuthenticatorAssertionResponse
  return {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    authenticatorAttachment: credential.authenticatorAttachment,
    clientExtensionResults: credential.getClientExtensionResults(),
    response: {
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
      authenticatorData: bufferToBase64url(response.authenticatorData),
      signature: bufferToBase64url(response.signature),
      userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
    },
  }
}
