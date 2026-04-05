using System;
using System.Linq;
using System.Text;
using System.Text.Json;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IDiscoveryService
{
    bool IsDiscoveryRequest(ReadOnlySpan<byte> payload);
    DiscoveryResponse CreateResponse(AppSettings settings, CapabilitiesModel capabilities);
    byte[] SerializeResponse(DiscoveryResponse response);
    QrConnectionPayload CreateQrPayload(AppSettings settings, string host);
}

public sealed class DiscoveryService : IDiscoveryService
{
    private static readonly byte[] MagicBytes = Encoding.ASCII.GetBytes(ProtocolConstants.DiscoveryMagic);
    private readonly IDiscoveryModelFactory _factory;

    public DiscoveryService(IDiscoveryModelFactory factory)
    {
        _factory = factory;
    }

    public bool IsDiscoveryRequest(ReadOnlySpan<byte> payload)
    {
        return payload.Length >= MagicBytes.Length && payload[..MagicBytes.Length].SequenceEqual(MagicBytes);
    }

    public DiscoveryResponse CreateResponse(AppSettings settings, CapabilitiesModel capabilities)
        => _factory.CreateDiscoveryResponse(settings, capabilities);

    public byte[] SerializeResponse(DiscoveryResponse response)
        => Encoding.UTF8.GetBytes(JsonSerializer.Serialize(response, ProtocolJson.SharedOptions));

    public QrConnectionPayload CreateQrPayload(AppSettings settings, string host)
        => _factory.CreateQrPayload(settings, host);
}
