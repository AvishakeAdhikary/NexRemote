using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text.Json;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IAuthenticationService
{
    bool TryParseAuthPayload(string payload, out AuthRequestMessage? message, out bool wasEncrypted);
    bool IsTrusted(string deviceId);
    TrustedDeviceRecord? GetTrustedDevice(string deviceId);
    void RecordTrust(string deviceId, string deviceName, string publicKey);
    string BuildAuthSuccess(AppSettings settings, CapabilitiesModel capabilities, IReadOnlyDictionary<string, FeatureStatusInfo> featureStatus);
    string BuildAuthChallenge(AppSettings settings, CapabilitiesModel capabilities, IReadOnlyDictionary<string, FeatureStatusInfo> featureStatus, string nonce);
    string BuildAuthFailed();
    string BuildConnectionRejected();
    bool TryParseAuthResponsePayload(string payload, out AuthResponseMessage? message);
    bool VerifyResponseSignature(string publicKey, string nonce, string signature);
}

public sealed class AuthenticationService : IAuthenticationService
{
    private readonly IMessageEncryptionService _crypto;
    private readonly ITrustedDeviceService _trustedDevices;

    public AuthenticationService(IMessageEncryptionService crypto, ITrustedDeviceService trustedDevices)
    {
        _crypto = crypto;
        _trustedDevices = trustedDevices;
    }

    public bool TryParseAuthPayload(string payload, out AuthRequestMessage? message, out bool wasEncrypted)
    {
        message = null;
        wasEncrypted = false;

        if (string.IsNullOrWhiteSpace(payload))
        {
            return false;
        }

        if (TryParsePlain(payload, out message))
        {
            return true;
        }

        try
        {
            wasEncrypted = true;
            var decrypted = _crypto.DecryptFromBase64(payload);
            return TryParsePlain(decrypted, out message);
        }
        catch
        {
            return false;
        }
    }

    public bool IsTrusted(string deviceId) => _trustedDevices.IsTrusted(deviceId);

    public TrustedDeviceRecord? GetTrustedDevice(string deviceId) => _trustedDevices.Get(deviceId);

    public void RecordTrust(string deviceId, string deviceName, string publicKey) => _trustedDevices.RecordConnection(deviceId, deviceName, publicKey);

    public string BuildAuthSuccess(AppSettings settings, CapabilitiesModel capabilities, IReadOnlyDictionary<string, FeatureStatusInfo> featureStatus)
    {
        var response = new
        {
            type = ProtocolConstants.AuthSuccessType,
            server_name = settings.PcName,
            capabilities,
            feature_status = featureStatus
        };

        return JsonSerializer.Serialize(response, ProtocolJson.SharedOptions);
    }

    public string BuildAuthChallenge(AppSettings settings, CapabilitiesModel capabilities, IReadOnlyDictionary<string, FeatureStatusInfo> featureStatus, string nonce)
    {
        var response = new
        {
            type = ProtocolConstants.AuthChallengeType,
            server_name = settings.PcName,
            nonce,
            capabilities,
            feature_status = featureStatus
        };

        return JsonSerializer.Serialize(response, ProtocolJson.SharedOptions);
    }

    public string BuildAuthFailed()
        => JsonSerializer.Serialize(new { type = ProtocolConstants.AuthFailedType }, ProtocolJson.SharedOptions);

    public string BuildConnectionRejected()
        => JsonSerializer.Serialize(new { type = ProtocolConstants.ConnectionRejectedType }, ProtocolJson.SharedOptions);

    public bool TryParseAuthResponsePayload(string payload, out AuthResponseMessage? message)
    {
        message = null;
        if (string.IsNullOrWhiteSpace(payload))
        {
            return false;
        }

        if (TryParseAuthResponsePlain(payload, out message))
        {
            return true;
        }

        try
        {
            var decrypted = _crypto.DecryptFromBase64(payload);
            return TryParseAuthResponsePlain(decrypted, out message);
        }
        catch
        {
            message = null;
            return false;
        }
    }

    public bool VerifyResponseSignature(string publicKey, string nonce, string signature)
    {
        if (string.IsNullOrWhiteSpace(publicKey) || string.IsNullOrWhiteSpace(nonce) || string.IsNullOrWhiteSpace(signature))
        {
            return false;
        }

        try
        {
            using var ecdsa = ECDsa.Create();
            ecdsa.ImportSubjectPublicKeyInfo(Convert.FromBase64String(publicKey), out _);
            var challengeBytes = Convert.FromBase64String(nonce);
            var signatureBytes = Convert.FromBase64String(signature);

            return ecdsa.VerifyData(
                       challengeBytes,
                       signatureBytes,
                       HashAlgorithmName.SHA256,
                       DSASignatureFormat.Rfc3279DerSequence)
                   || ecdsa.VerifyData(
                       challengeBytes,
                       signatureBytes,
                       HashAlgorithmName.SHA256,
                       DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        }
        catch
        {
            return false;
        }
    }

    private static bool TryParsePlain(string payload, out AuthRequestMessage? message)
    {
        try
        {
            message = JsonSerializer.Deserialize<AuthRequestMessage>(payload, ProtocolJson.SharedOptions);
            return message is not null
                   && string.Equals(message.Type, ProtocolConstants.AuthType, StringComparison.OrdinalIgnoreCase)
                   && !string.IsNullOrWhiteSpace(message.DeviceId)
                   && !string.IsNullOrWhiteSpace(message.DeviceName);
        }
        catch
        {
            message = null;
            return false;
        }
    }

    private static bool TryParseAuthResponsePlain(string payload, out AuthResponseMessage? message)
    {
        try
        {
            message = JsonSerializer.Deserialize<AuthResponseMessage>(payload, ProtocolJson.SharedOptions);
            return message is not null &&
                   string.Equals(message.Type, ProtocolConstants.AuthResponseType, StringComparison.OrdinalIgnoreCase) &&
                   !string.IsNullOrWhiteSpace(message.DeviceId) &&
                   !string.IsNullOrWhiteSpace(message.Signature);
        }
        catch
        {
            message = null;
            return false;
        }
    }
}
