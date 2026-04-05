using System;
using System.Buffers;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using NexRemote.Models;

namespace NexRemote.Services;

public sealed partial class RemoteServerHost
{
    private async Task HandleClientAsync(WebSocket socket, CancellationToken cancellationToken)
    {
        RemoteClientSession? session = null;
        string? clientId = null;
        string? deviceName = null;

        try
        {
            var authPayload = await ReceiveTextMessageAsync(socket, TimeSpan.FromSeconds(30), cancellationToken).ConfigureAwait(false);
            if (string.IsNullOrWhiteSpace(authPayload))
            {
                return;
            }

            if (!_authenticationService.TryParseAuthPayload(authPayload, out var authMessage, out _))
            {
                _logger.LogInformation("Rejected websocket client because the auth payload could not be parsed.");
                await SendPlainAsync(socket, _authenticationService.BuildAuthFailed(), cancellationToken).ConfigureAwait(false);
                return;
            }

            clientId = authMessage!.DeviceId;
            deviceName = authMessage.DeviceName;

            if (!Settings.EnableRemoteAccess)
            {
                _logger.LogInformation("Rejected client {ClientId} because remote access is disabled.", clientId);
                await SendPlainAsync(socket, _authenticationService.BuildConnectionRejected(), cancellationToken).ConfigureAwait(false);
                return;
            }

            if (Settings.MaxClients > 0 && !_sessions.ContainsKey(clientId) && _sessions.Count >= Settings.MaxClients)
            {
                _logger.LogInformation("Rejected client {ClientId} because the server is at capacity.", clientId);
                await SendPlainAsync(socket, _authenticationService.BuildConnectionRejected(), cancellationToken).ConfigureAwait(false);
                return;
            }

            var trusted = _authenticationService.IsTrusted(clientId);
            if (!trusted && Settings.RequireApproval)
            {
                trusted = await _approvalService.RequestApprovalAsync(
                    clientId,
                    deviceName,
                    TimeSpan.FromSeconds(ProtocolConstants.ApprovalTimeoutSeconds),
                    cancellationToken).ConfigureAwait(false);
                if (!trusted)
                {
                    _logger.LogInformation("Rejected client {ClientId} because approval was denied or timed out.", clientId);
                    await SendPlainAsync(socket, _authenticationService.BuildConnectionRejected(), cancellationToken).ConfigureAwait(false);
                    return;
                }
            }

            _authenticationService.RecordTrust(clientId, deviceName);
            await _trustedDeviceService.SaveAsync(cancellationToken).ConfigureAwait(false);

            session = new RemoteClientSession(clientId, deviceName, socket);
            RegisterSession(session);

            _logger.LogInformation("Accepted client {ClientId} ({DeviceName}).", clientId, deviceName);
            await SendPlainAsync(socket, _authenticationService.BuildAuthSuccess(Settings, Capabilities), cancellationToken).ConfigureAwait(false);
            RaiseClientConnected(clientId, deviceName);

            await ProcessMessagesAsync(session, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
            // shutting down
        }
        catch (Exception ex)
        {
            _logger.LogDebug(ex, "Client session ended");
        }
        finally
        {
            if (session is not null)
            {
                UnregisterSession(session.ClientId);
                session.StopAllBackgroundWork();
                session.Abort();
                RaiseClientDisconnected(session.ClientId, session.DeviceName);
            }
        }
    }

    private async Task ProcessMessagesAsync(RemoteClientSession session, CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested && session.Socket.State == WebSocketState.Open)
        {
            var payload = await ReceiveTextMessageAsync(session.Socket, Timeout.InfiniteTimeSpan, cancellationToken).ConfigureAwait(false);
            if (payload is null)
            {
                break;
            }

            if (!TryParseInboundMessage(payload, out var message))
            {
                continue;
            }

            if (IsPing(message))
            {
                await SendPlainAsync(session.Socket, JsonSerializer.Serialize(new { type = ProtocolConstants.PongType }, ProtocolJson.SharedOptions), cancellationToken).ConfigureAwait(false);
                continue;
            }

            var protocolMessage = JsonSerializer.Deserialize<ProtocolMessage>(message.GetRawText(), ProtocolJson.SharedOptions);
            if (protocolMessage is not null)
            {
                RaiseMessageReceived(session.ClientId, protocolMessage);
            }

            var type = GetString(message, "type").ToLowerInvariant();
            switch (type)
            {
                case ProtocolConstants.AuthType:
                    break;
                case "keyboard":
                    _inputService.SendKeyboard(message);
                    break;
                case "mouse":
                    _inputService.SendMouse(message);
                    break;
                case "gamepad":
                case "gamepad_xinput":
                case "gamepad_android":
                    break;
                case "gamepad_dinput":
                    UpdateCapabilities(Capabilities.GamepadAvailable, "dinput");
                    break;
                case "gamepad_mode":
                    session.GamepadMode = GetString(message, "mode", _gamepadMode);
                    RefreshCapabilities();
                    UpdateCapabilities(Capabilities.GamepadAvailable, session.GamepadMode);
                    await SendEncryptedAsync(session, new
                    {
                        type = "gamepad_mode",
                        mode = _gamepadMode,
                        status = new { available = Capabilities.GamepadAvailable, mode = _gamepadMode }
                    }, cancellationToken).ConfigureAwait(false);
                    break;
                case "macro":
                    if (message.TryGetProperty("steps", out var steps))
                    {
                        await _inputService.ReplayMacroAsync(steps, cancellationToken).ConfigureAwait(false);
                    }
                    break;
                case "camera":
                    if (!Settings.CameraAccessConsentGranted)
                    {
                        await SendEncryptedAsync(session, new
                        {
                            type = "camera",
                            action = "permission_required",
                            permission = "camera"
                        }, cancellationToken).ConfigureAwait(false);
                        break;
                    }

                    await HandleCameraAsync(session, message, cancellationToken).ConfigureAwait(false);
                    break;
                case "file_explorer":
                    await SendEncryptedAsync(session, await _fileExplorerService.HandleRequestAsync(message).ConfigureAwait(false), cancellationToken).ConfigureAwait(false);
                    break;
                case "screen_share":
                    await HandleScreenShareAsync(session, message, cancellationToken).ConfigureAwait(false);
                    break;
                case "media_control":
                    await HandleMediaControlAsync(session, message, cancellationToken).ConfigureAwait(false);
                    break;
                case "task_manager":
                    await SendEncryptedAsync(session, await _taskManagerService.HandleRequestAsync(message).ConfigureAwait(false), cancellationToken).ConfigureAwait(false);
                    break;
                case "clipboard":
                    break;
                default:
                    _logger.LogDebug("Unknown message type: {MessageType}", type);
                    break;
            }
        }
    }

    private bool TryParseInboundMessage(string payload, out JsonElement message)
    {
        message = default;
        if (TryParseJson(payload, out message))
        {
            return true;
        }

        try
        {
            var decrypted = _encryptionService.DecryptFromBase64(payload);
            return TryParseJson(decrypted, out message);
        }
        catch
        {
            return false;
        }
    }

    private static bool TryParseJson(string payload, out JsonElement element)
    {
        try
        {
            using var document = JsonDocument.Parse(payload);
            element = document.RootElement.Clone();
            return true;
        }
        catch
        {
            element = default;
            return false;
        }
    }

    private static bool IsPing(JsonElement message)
        => string.Equals(GetString(message, "type"), ProtocolConstants.PingType, StringComparison.OrdinalIgnoreCase);

    private static async Task<string?> ReceiveTextMessageAsync(WebSocket socket, TimeSpan timeout, CancellationToken cancellationToken)
    {
        using var timeoutCts = timeout == Timeout.InfiniteTimeSpan ? null : new CancellationTokenSource(timeout);
        using var linkedCts = timeoutCts is null
            ? CancellationTokenSource.CreateLinkedTokenSource(cancellationToken)
            : CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token);

        var buffer = ArrayPool<byte>.Shared.Rent(4096);
        try
        {
            using var stream = new MemoryStream();
            while (true)
            {
                var result = await socket.ReceiveAsync(buffer.AsMemory(0, buffer.Length), linkedCts.Token).ConfigureAwait(false);
                if (result.MessageType == WebSocketMessageType.Close)
                {
                    return null;
                }

                stream.Write(buffer, 0, result.Count);
                if (result.EndOfMessage)
                {
                    break;
                }
            }

            return Encoding.UTF8.GetString(stream.ToArray());
        }
        catch (OperationCanceledException)
        {
            return null;
        }
        catch (WebSocketException)
        {
            return null;
        }
        finally
        {
            ArrayPool<byte>.Shared.Return(buffer);
        }
    }

    private static async Task SendPlainAsync(WebSocket socket, string payload, CancellationToken cancellationToken)
    {
        var bytes = Encoding.UTF8.GetBytes(payload);
        await socket.SendAsync(bytes, WebSocketMessageType.Text, true, cancellationToken).ConfigureAwait(false);
    }

    private async Task SendEncryptedAsync(RemoteClientSession session, object payload, CancellationToken cancellationToken)
    {
        var json = JsonSerializer.Serialize(payload, ProtocolJson.SharedOptions);
        var encrypted = _encryptionService.EncryptToBase64(json);
        await session.SendTextAsync(encrypted, cancellationToken).ConfigureAwait(false);
    }

    private static byte[] BuildBinaryFrame(string header, byte index, byte[] payload)
    {
        var headerBytes = Encoding.ASCII.GetBytes(header);
        var result = new byte[headerBytes.Length + 1 + payload.Length];
        Buffer.BlockCopy(headerBytes, 0, result, 0, headerBytes.Length);
        result[headerBytes.Length] = index;
        Buffer.BlockCopy(payload, 0, result, headerBytes.Length + 1, payload.Length);
        return result;
    }
}
