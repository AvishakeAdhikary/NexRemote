using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

namespace NexRemote.Services;

public sealed partial class RemoteServerHost
{
    private sealed class RemoteClientSession
    {
        private readonly SemaphoreSlim _sendGate = new(1, 1);

        public RemoteClientSession(string clientId, string deviceName, WebSocket socket)
        {
            ClientId = clientId;
            DeviceName = deviceName;
            Socket = socket;
        }

        public string ClientId { get; }
        public string DeviceName { get; }
        public WebSocket Socket { get; }
        public string GamepadMode { get; set; } = "xinput";
        public int ScreenFps { get; set; } = 30;
        public int ScreenQuality { get; set; } = 70;
        public string ScreenResolution { get; set; } = "native";
        public int ScreenPreferredMonitor { get; set; }
        public ConcurrentDictionary<int, CancellationTokenSource> ScreenTasks { get; } = new();
        public ConcurrentDictionary<int, CancellationTokenSource> CameraTasks { get; } = new();
        public ConcurrentDictionary<int, bool> ActiveCameras { get; } = new();
        public CancellationTokenSource? MediaLoopCts { get; set; }
        public Task? MediaLoopTask { get; set; }

        public async Task SendTextAsync(string payload, CancellationToken cancellationToken = default)
        {
            var bytes = Encoding.UTF8.GetBytes(payload);
            await SendAsync(bytes, WebSocketMessageType.Text, cancellationToken).ConfigureAwait(false);
        }

        public async Task SendBinaryAsync(byte[] payload, CancellationToken cancellationToken = default)
        {
            await SendAsync(payload, WebSocketMessageType.Binary, cancellationToken).ConfigureAwait(false);
        }

        public void StopAllBackgroundWork()
        {
            foreach (var pair in ScreenTasks.ToArray())
            {
                if (ScreenTasks.TryRemove(pair.Key, out var cts))
                {
                    cts.Cancel();
                    cts.Dispose();
                }
            }

            foreach (var pair in ActiveCameras.ToArray())
            {
                ActiveCameras.TryRemove(pair.Key, out _);
            }

            foreach (var pair in CameraTasks.ToArray())
            {
                if (CameraTasks.TryRemove(pair.Key, out var cts))
                {
                    cts.Cancel();
                    cts.Dispose();
                }
            }

            if (MediaLoopCts is not null)
            {
                MediaLoopCts.Cancel();
                MediaLoopCts.Dispose();
                MediaLoopCts = null;
            }
        }

        public void Abort()
        {
            try
            {
                Socket.Abort();
            }
            catch
            {
                // ignored
            }
        }

        private async Task SendAsync(byte[] payload, WebSocketMessageType messageType, CancellationToken cancellationToken)
        {
            if (Socket.State != WebSocketState.Open)
            {
                return;
            }

            await _sendGate.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                if (Socket.State == WebSocketState.Open)
                {
                    await Socket.SendAsync(payload.AsMemory(), messageType, true, cancellationToken).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException)
            {
                // ignored
            }
            catch (WebSocketException)
            {
                // ignored
            }
            finally
            {
                _sendGate.Release();
            }
        }
    }
}
