using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IServerCoordinator
{
    bool IsRunning { get; }
    AppSettings Settings { get; }
    CapabilitiesModel Capabilities { get; }
    IReadOnlyDictionary<string, FeatureStatusInfo> FeatureStatus { get; }
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
}

public sealed class ServerCoordinator : IServerCoordinator
{
    private readonly IRemoteServer _remoteServer;
    private readonly IAdbBridgeService _adbBridgeService;

    public ServerCoordinator(IRemoteServer remoteServer, IAdbBridgeService adbBridgeService)
    {
        _remoteServer = remoteServer;
        _adbBridgeService = adbBridgeService;
        _remoteServer.ClientConnected += (_, args) => ClientConnected?.Invoke(this, args);
        _remoteServer.ClientDisconnected += (_, args) => ClientDisconnected?.Invoke(this, args);
        _remoteServer.MessageReceived += (_, args) => MessageReceived?.Invoke(this, args);
    }

    public bool IsRunning => _remoteServer.IsRunning;

    public AppSettings Settings => _remoteServer.Settings;

    public CapabilitiesModel Capabilities => _remoteServer.Capabilities;

    public IReadOnlyDictionary<string, FeatureStatusInfo> FeatureStatus => _remoteServer.GetFeatureStatus();

    public event EventHandler<ClientConnectionEventArgs>? ClientConnected;
    public event EventHandler<ClientConnectionEventArgs>? ClientDisconnected;
    public event EventHandler<ServerMessageEventArgs>? MessageReceived;

    public async Task StartAsync(CancellationToken cancellationToken = default)
    {
        await _adbBridgeService.InitializeAsync(cancellationToken).ConfigureAwait(false);
        _remoteServer.RefreshCapabilities();
        await _remoteServer.StartAsync(cancellationToken).ConfigureAwait(false);
    }

    public async Task StopAsync(CancellationToken cancellationToken = default)
    {
        await _remoteServer.StopAsync(cancellationToken).ConfigureAwait(false);
        await _adbBridgeService.StopAsync(cancellationToken).ConfigureAwait(false);
    }

    public Task DisconnectClientAsync(string clientId, CancellationToken cancellationToken = default)
        => _remoteServer.DisconnectClientAsync(clientId, cancellationToken);

    public void RefreshCapabilities() => _remoteServer.RefreshCapabilities();

    public DiscoveryResponse CreateDiscoveryResponse() => _remoteServer.CreateDiscoveryResponse();

    public QrConnectionPayload CreateQrPayload(string host) => _remoteServer.CreateQrPayload(host);

    public IReadOnlyDictionary<string, TrustedDeviceRecord> GetTrustedDevices() => _remoteServer.GetTrustedDevices();
}
