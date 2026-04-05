using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Models;

namespace NexRemote.Services;

public sealed class ClientConnectionEventArgs : EventArgs
{
    public ClientConnectionEventArgs(string clientId, string deviceName)
    {
        ClientId = clientId;
        DeviceName = deviceName;
    }

    public string ClientId { get; }
    public string DeviceName { get; }
}

public sealed class ServerMessageEventArgs : EventArgs
{
    public ServerMessageEventArgs(string clientId, ProtocolMessage message)
    {
        ClientId = clientId;
        Message = message;
    }

    public string ClientId { get; }
    public ProtocolMessage Message { get; }
}

public sealed class PendingApprovalRequestEventArgs : EventArgs
{
    public PendingApprovalRequestEventArgs(string deviceId, string deviceName)
    {
        DeviceId = deviceId;
        DeviceName = deviceName;
    }

    public string DeviceId { get; }
    public string DeviceName { get; }
}

public interface IRemoteServer
{
    bool IsRunning { get; }
    AppSettings Settings { get; }
    CapabilitiesModel Capabilities { get; }

    event EventHandler<ClientConnectionEventArgs>? ClientConnected;
    event EventHandler<ClientConnectionEventArgs>? ClientDisconnected;
    event EventHandler<ServerMessageEventArgs>? MessageReceived;

    Task StartAsync(CancellationToken cancellationToken = default);
    Task StopAsync(CancellationToken cancellationToken = default);
    Task DisconnectClientAsync(string clientId, CancellationToken cancellationToken = default);
    void RefreshCapabilities();
    DiscoveryResponse CreateDiscoveryResponse();
    QrConnectionPayload CreateQrPayload(string host);
    IReadOnlyDictionary<string, TrustedDeviceRecord> GetTrustedDevices();
    IReadOnlyDictionary<string, FeatureStatusInfo> GetFeatureStatus();
}

public interface IConnectionApprovalService
{
    event EventHandler<PendingApprovalRequestEventArgs>? ApprovalRequested;

    Task<bool> RequestApprovalAsync(string deviceId, string deviceName, TimeSpan timeout, CancellationToken cancellationToken = default);
    void CompleteApproval(string deviceId, bool approved);
}
