using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using NexRemote.Helpers;
using NexRemote.Models;

namespace NexRemote.Services;

public sealed partial class RemoteServerHost : IRemoteServer
{
    private readonly IAppSettingsService _settingsService;
    private readonly ITrustedDeviceService _trustedDeviceService;
    private readonly IDiscoveryService _discoveryService;
    private readonly IServerCapabilitiesFactory _capabilitiesFactory;
    private readonly IAuthenticationService _authenticationService;
    private readonly IConnectionApprovalService _approvalService;
    private readonly IMessageEncryptionService _encryptionService;
    private readonly ICertificateService _certificateService;
    private readonly IGamepadDriverService _gamepadDriverService;
    private readonly IGamepadTransportService _gamepadTransportService;
    private readonly IAdbBridgeService _adbBridgeService;
    private readonly IClipboardService _clipboardService;
    private readonly ILogger<RemoteServerHost> _logger;

    private readonly NativeInputService _inputService = new();
    private readonly FileExplorerService _fileExplorerService = new();
    private readonly TaskManagerService _taskManagerService = new();
    private readonly MediaControlService _mediaControlService = new();
    private readonly ScreenCaptureService _screenCaptureService = new();
    private readonly CameraCaptureService _cameraCaptureService = new();
    private readonly ConcurrentDictionary<string, RemoteClientSession> _sessions = new(StringComparer.OrdinalIgnoreCase);
    private readonly SemaphoreSlim _lifecycleGate = new(1, 1);
    private readonly object _sessionLock = new();
    private readonly ServerState _state = new();

    private WebApplication? _app;
    private CancellationTokenSource? _serverCts;
    private Task? _discoveryTask;
    private string _gamepadMode = "xinput";

    public RemoteServerHost(
        IAppSettingsService settingsService,
        ITrustedDeviceService trustedDeviceService,
        IDiscoveryService discoveryService,
        IServerCapabilitiesFactory capabilitiesFactory,
        IAuthenticationService authenticationService,
        IConnectionApprovalService approvalService,
        IMessageEncryptionService encryptionService,
        ICertificateService certificateService,
        IGamepadDriverService gamepadDriverService,
        IGamepadTransportService gamepadTransportService,
        IAdbBridgeService adbBridgeService,
        IClipboardService clipboardService,
        ILogger<RemoteServerHost> logger)
    {
        _settingsService = settingsService;
        _trustedDeviceService = trustedDeviceService;
        _discoveryService = discoveryService;
        _capabilitiesFactory = capabilitiesFactory;
        _authenticationService = authenticationService;
        _approvalService = approvalService;
        _encryptionService = encryptionService;
        _certificateService = certificateService;
        _gamepadDriverService = gamepadDriverService;
        _gamepadTransportService = gamepadTransportService;
        _adbBridgeService = adbBridgeService;
        _clipboardService = clipboardService;
        _logger = logger;
        RefreshCapabilities();
    }

    public bool IsRunning => _state.Running;

    public AppSettings Settings => _settingsService.Current;

    public CapabilitiesModel Capabilities { get; private set; } = new();

    public event EventHandler<ClientConnectionEventArgs>? ClientConnected;
    public event EventHandler<ClientConnectionEventArgs>? ClientDisconnected;
    public event EventHandler<ServerMessageEventArgs>? MessageReceived;

    public DiscoveryResponse CreateDiscoveryResponse()
        => _discoveryService.CreateResponse(Settings, Capabilities);

    public QrConnectionPayload CreateQrPayload(string host)
        => _discoveryService.CreateQrPayload(Settings, host);

    public IReadOnlyDictionary<string, TrustedDeviceRecord> GetTrustedDevices()
        => _trustedDeviceService.Devices;

    public IReadOnlyDictionary<string, FeatureStatusInfo> GetFeatureStatus()
        => CreateFeatureStatus();

    public void UpdateCapabilities(bool gamepadAvailable, string gamepadMode)
    {
        _gamepadMode = string.IsNullOrWhiteSpace(gamepadMode) ? "xinput" : gamepadMode;
        Capabilities = _capabilitiesFactory.Create(gamepadAvailable, _gamepadMode);
    }

    public void RefreshCapabilities()
    {
        var gamepadAvailable = _gamepadDriverService.IsNativeTransportReady() && _gamepadTransportService.IsReady;
        UpdateCapabilities(gamepadAvailable, _gamepadMode);
        Capabilities.Gamepad = gamepadAvailable;
        Capabilities.CameraStreaming = Settings.CameraAccessConsentGranted;
        Capabilities.Clipboard = true;
    }

    public void RaiseClientConnected(string clientId, string deviceName)
        => ClientConnected?.Invoke(this, new ClientConnectionEventArgs(clientId, deviceName));

    public void RaiseClientDisconnected(string clientId, string deviceName)
        => ClientDisconnected?.Invoke(this, new ClientConnectionEventArgs(clientId, deviceName));

    public void RaiseMessageReceived(string clientId, ProtocolMessage message)
        => MessageReceived?.Invoke(this, new ServerMessageEventArgs(clientId, message));

    public async Task StartAsync(CancellationToken cancellationToken = default)
    {
        await _lifecycleGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (_state.Running)
            {
                return;
            }

            RefreshCapabilities();
            await _certificateService.EnsureCertificateAsync(cancellationToken).ConfigureAwait(false);
            using var pemCertificate = X509Certificate2.CreateFromPemFile(_certificateService.CertificatePath, _certificateService.PrivateKeyPath);
            var certificate = new X509Certificate2(pemCertificate.Export(X509ContentType.Pkcs12));

            var builder = WebApplication.CreateBuilder(new WebApplicationOptions
            {
                ApplicationName = typeof(RemoteServerHost).Assembly.FullName,
                ContentRootPath = AppContext.BaseDirectory
            });

            builder.WebHost.UseKestrel(options =>
            {
                options.ListenAnyIP(Settings.ServerPortInsecure);
                options.ListenAnyIP(Settings.ServerPort, listenOptions =>
                {
                    listenOptions.UseHttps(httpsOptions => httpsOptions.ServerCertificate = certificate);
                });
            });

            var app = builder.Build();
            var serverCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);

            app.UseWebSockets();
            app.Use(async (context, next) =>
            {
                if (context.WebSockets.IsWebSocketRequest)
                {
                    using var socket = await context.WebSockets.AcceptWebSocketAsync().ConfigureAwait(false);
                    await HandleClientAsync(socket, context.Request.IsHttps, serverCts.Token).ConfigureAwait(false);
                    return;
                }

                if (context.Request.Path == "/")
                {
                    context.Response.StatusCode = StatusCodes.Status200OK;
                    await context.Response.WriteAsync("NexRemote").ConfigureAwait(false);
                    return;
                }

                await next().ConfigureAwait(false);
            });

            _app = app;
            _serverCts = serverCts;

            await app.StartAsync(serverCts.Token).ConfigureAwait(false);
            _discoveryTask = RunDiscoveryLoopAsync(serverCts.Token);
            _state.Running = true;
            _state.LastHost = null;
        }
        catch
        {
            await StopCoreAsync(CancellationToken.None).ConfigureAwait(false);
            throw;
        }
        finally
        {
            _lifecycleGate.Release();
        }
    }

    public async Task StopAsync(CancellationToken cancellationToken = default)
    {
        await _lifecycleGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await StopCoreAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _lifecycleGate.Release();
        }
    }

    public async Task DisconnectClientAsync(string clientId, CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(clientId))
        {
            return;
        }

        if (!_sessions.TryGetValue(clientId, out var session))
        {
            return;
        }

        try
        {
            if (session.Socket.State == WebSocketState.Open || session.Socket.State == WebSocketState.CloseReceived)
            {
                await session.Socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Disconnected by server", cancellationToken).ConfigureAwait(false);
            }
        }
        catch
        {
            session.Abort();
        }
    }

    private async Task StopCoreAsync(CancellationToken cancellationToken)
    {
        _state.Running = false;

        foreach (var session in _sessions.Values)
        {
            session.StopAllBackgroundWork();
            session.Abort();
        }

        _sessions.Clear();
        _state.ConnectedClients = 0;

        if (_serverCts is not null)
        {
            try
            {
                _serverCts.Cancel();
            }
            catch
            {
                // ignored
            }
        }

        if (_app is not null)
        {
            try
            {
                await _app.StopAsync(cancellationToken).ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "StopAsync failed");
            }
        }

        if (_discoveryTask is not null)
        {
            try
            {
                await _discoveryTask.ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "Discovery task ended with error");
            }
        }

        if (_app is not null)
        {
            await _app.DisposeAsync().ConfigureAwait(false);
            _app = null;
        }

        _serverCts?.Dispose();
        _serverCts = null;
        _discoveryTask = null;
    }

    private async Task RunDiscoveryLoopAsync(CancellationToken cancellationToken)
    {
        using var udp = new UdpClient(AddressFamily.InterNetwork);
        udp.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        udp.Client.Bind(new IPEndPoint(IPAddress.Any, Settings.DiscoveryPort));

        try
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                var receiveTask = udp.ReceiveAsync();
                var completedTask = await Task.WhenAny(receiveTask, Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken)).ConfigureAwait(false);
                if (completedTask != receiveTask)
                {
                    break;
                }

                UdpReceiveResult result;
                try
                {
                    result = await receiveTask.ConfigureAwait(false);
                }
                catch (ObjectDisposedException)
                {
                    break;
                }
                catch (SocketException)
                {
                    break;
                }

                if (!_discoveryService.IsDiscoveryRequest(result.Buffer))
                {
                    continue;
                }

                var response = CreateDiscoveryResponse();
                var payload = _discoveryService.SerializeResponse(response);
                await udp.SendAsync(payload, payload.Length, result.RemoteEndPoint).ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            _logger.LogDebug(ex, "Discovery loop stopped");
        }
    }

    private void RegisterSession(RemoteClientSession session)
    {
        lock (_sessionLock)
        {
            if (_sessions.TryRemove(session.ClientId, out var existing))
            {
                existing.StopAllBackgroundWork();
                existing.Abort();
            }
            else
            {
                _state.ConnectedClients++;
            }

            _sessions[session.ClientId] = session;
        }
    }

    private void UnregisterSession(string clientId)
    {
        lock (_sessionLock)
        {
            if (_sessions.TryRemove(clientId, out var session))
            {
                session.StopAllBackgroundWork();
                if (_state.ConnectedClients > 0)
                {
                    _state.ConnectedClients--;
                }
            }
        }
    }

    private static string GetString(JsonElement element, string propertyName, string fallback = "")
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var prop) &&
            prop.ValueKind == JsonValueKind.String)
        {
            return prop.GetString() ?? fallback;
        }

        return fallback;
    }

    private static int ReadInt32(JsonElement element, string propertyName, int fallback = 0)
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var prop) &&
            prop.TryGetInt32(out var value))
        {
            return value;
        }

        return fallback;
    }

    private static List<int> ReadIntArray(JsonElement element, string propertyName)
    {
        var result = new List<int>();
        if (element.ValueKind != JsonValueKind.Object ||
            !element.TryGetProperty(propertyName, out var prop) ||
            prop.ValueKind != JsonValueKind.Array)
        {
            return result;
        }

        foreach (var item in prop.EnumerateArray())
        {
            if (item.TryGetInt32(out var value))
            {
                result.Add(value);
            }
        }

        return result;
    }

    private IReadOnlyDictionary<string, FeatureStatusInfo> CreateFeatureStatus()
    {
        var gamepadAvailable = _gamepadDriverService.IsNativeTransportReady() && _gamepadTransportService.IsReady;
        var gamepadDriverInstalled = _gamepadDriverService.IsViGEmBusInstalled();
        var adbStatus = _adbBridgeService.CurrentStatus;

        return new Dictionary<string, FeatureStatusInfo>(StringComparer.OrdinalIgnoreCase)
        {
            ["touchpad"] = Available("Remote pointer and keyboard control are ready."),
            ["media_control"] = Available("Media control is ready."),
            ["screen_share"] = Available("Screen sharing is ready."),
            ["file_explorer"] = Available("File explorer is ready."),
            ["task_manager"] = Available("Task manager is ready."),
            ["clipboard"] = Available("Clipboard sync is ready."),
            ["camera"] = Settings.CameraAccessConsentGranted
                ? Available("Camera streaming is ready.")
                : Unavailable("Camera streaming requires local consent on the PC.", "grant_camera_consent"),
            ["gamepad"] = gamepadAvailable
                ? Available("Native gamepad transport is ready.")
                : gamepadDriverInstalled
                    ? Unavailable("ViGEmBus is installed, but the virtual controller backend is still initializing or needs the host restarted cleanly.", "restart_server")
                    : Unavailable("Install ViGEmBus to enable native gamepad transport.", "install_vigem"),
            ["usb_bridge"] = adbStatus.ToolAvailable
                ? adbStatus.ReverseActive
                    ? Available(adbStatus.Reason)
                    : Unavailable(adbStatus.Reason, adbStatus.DeviceAuthorized ? "connect_device" : "authorize_device")
                : Unavailable("ADB platform-tools are not bundled or installed yet.", "install_platform_tools")
        };
    }

    private static FeatureStatusInfo Available(string reason) => new()
    {
        Supported = true,
        Available = true,
        Reason = reason
    };

    private static FeatureStatusInfo Unavailable(string reason, string actionRequired) => new()
    {
        Supported = true,
        Available = false,
        Reason = reason,
        ActionRequired = actionRequired
    };
}
