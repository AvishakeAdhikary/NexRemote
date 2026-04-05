using System;
using System.Text.Json;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IAuthenticationService
{
    bool TryParseAuthPayload(string payload, out AuthRequestMessage? message, out bool wasEncrypted);
    bool IsTrusted(string deviceId);
    void RecordTrust(string deviceId, string deviceName);
    string BuildAuthSuccess(AppSettings settings, CapabilitiesModel capabilities);
    string BuildAuthFailed();
    string BuildConnectionRejected();
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

    public void RecordTrust(string deviceId, string deviceName) => _trustedDevices.RecordConnection(deviceId, deviceName);

    public string BuildAuthSuccess(AppSettings settings, CapabilitiesModel capabilities)
    {
        var response = new
        {
            type = ProtocolConstants.AuthSuccessType,
            server_name = settings.PcName,
            capabilities
        };

        return JsonSerializer.Serialize(response, ProtocolJson.SharedOptions);
    }

    public string BuildAuthFailed()
        => JsonSerializer.Serialize(new { type = ProtocolConstants.AuthFailedType }, ProtocolJson.SharedOptions);

    public string BuildConnectionRejected()
        => JsonSerializer.Serialize(new { type = ProtocolConstants.ConnectionRejectedType }, ProtocolJson.SharedOptions);

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
}
