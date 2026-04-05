using NexRemote.Models;

namespace NexRemote.Services;

public interface IDiscoveryModelFactory
{
    DiscoveryResponse CreateDiscoveryResponse(AppSettings settings, CapabilitiesModel capabilities);
    QrConnectionPayload CreateQrPayload(AppSettings settings, string host);
}

public sealed class DiscoveryModelFactory : IDiscoveryModelFactory
{
    public DiscoveryResponse CreateDiscoveryResponse(AppSettings settings, CapabilitiesModel capabilities)
    {
        return new DiscoveryResponse
        {
            Name = settings.PcName,
            Port = settings.ServerPort,
            PortInsecure = settings.ServerPortInsecure,
            Id = settings.DeviceId,
            Version = ProtocolConstants.Version
        };
    }

    public QrConnectionPayload CreateQrPayload(AppSettings settings, string host)
    {
        return new QrConnectionPayload
        {
            Host = host,
            Port = settings.ServerPort,
            PortInsecure = settings.ServerPortInsecure,
            Name = settings.PcName,
            Id = settings.DeviceId
        };
    }
}
