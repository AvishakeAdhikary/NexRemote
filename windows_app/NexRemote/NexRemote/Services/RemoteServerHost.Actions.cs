using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Net.WebSockets;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace NexRemote.Services;

public sealed partial class RemoteServerHost
{
    private async Task HandleScreenShareAsync(RemoteClientSession session, JsonElement message, CancellationToken cancellationToken)
    {
        var action = GetString(message, "action").ToLowerInvariant();
        switch (action)
        {
            case "start":
            {
                session.ScreenFps = Math.Max(1, ReadInt32(message, "fps", session.ScreenFps));
                session.ScreenQuality = Math.Clamp(ReadInt32(message, "quality", session.ScreenQuality), 1, 100);
                session.ScreenResolution = GetString(message, "resolution", session.ScreenResolution);

                var indices = ReadIntArray(message, "display_indices");
                if (indices.Count == 0)
                {
                    indices.Add(ReadInt32(message, "display_index", 0));
                }

                foreach (var index in indices)
                {
                    StartScreenStream(session, index, cancellationToken);
                }

                break;
            }
            case "stop":
            {
                var stopIndex = message.TryGetProperty("display_index", out var prop) && prop.TryGetInt32(out var index) ? (int?)index : null;
                StopScreenStreams(session, stopIndex);
                break;
            }
            case "set_quality":
                session.ScreenQuality = Math.Clamp(ReadInt32(message, "quality", session.ScreenQuality), 1, 100);
                break;
            case "set_resolution":
                session.ScreenResolution = GetString(message, "resolution", session.ScreenResolution);
                break;
            case "set_fps":
                session.ScreenFps = Math.Max(1, ReadInt32(message, "fps", session.ScreenFps));
                break;
            case "set_monitor":
                session.ScreenPreferredMonitor = ReadInt32(message, "monitor_index", session.ScreenPreferredMonitor);
                break;
            case "list_displays":
            {
                var monitors = _screenCaptureService.GetMonitors();
                await SendEncryptedAsync(session, new
                {
                    type = "screen_share",
                    action = "display_list",
                    displays = monitors.Select(display => new
                    {
                        index = display.Index,
                        name = display.Name,
                        width = display.Width,
                        height = display.Height,
                        is_primary = display.IsPrimary
                    }).ToArray(),
                    active_displays = session.ScreenTasks.Keys.OrderBy(value => value).ToArray(),
                    current_resolution = session.ScreenResolution,
                    current_fps = session.ScreenFps,
                    current_quality = session.ScreenQuality
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "input":
                _inputService.SendMouse(message);
                break;
        }
    }

    private async Task HandleMediaControlAsync(RemoteClientSession session, JsonElement message, CancellationToken cancellationToken)
    {
        if (session.MediaLoopTask is null || session.MediaLoopTask.IsCompleted)
        {
            StartMediaLoop(session, cancellationToken);
        }

        var response = await _mediaControlService.HandleRequestAsync(message).ConfigureAwait(false);
        if (response is not null)
        {
            await SendEncryptedAsync(session, response, cancellationToken).ConfigureAwait(false);
        }
    }

    private async Task HandleCameraAsync(RemoteClientSession session, JsonElement message, CancellationToken cancellationToken)
    {
        var action = GetString(message, "action").ToLowerInvariant();
        switch (action)
        {
            case "list_cameras":
            {
                var cameras = await _cameraCaptureService.GetCamerasAsync().ConfigureAwait(false);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "camera_list",
                    cameras
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "start":
            {
                var index = ReadInt32(message, "camera_index", 0);
                session.ActiveCameras[index] = true;
                _cameraCaptureService.StartCamera(index);
                StartCameraStream(session, index, cancellationToken);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "started",
                    camera_index = index,
                    camera_info = _cameraCaptureService.GetCameraInfo(index)
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "start_multi":
            {
                var indices = ReadIntArray(message, "camera_indices");
                foreach (var index in indices)
                {
                    session.ActiveCameras[index] = true;
                    _cameraCaptureService.StartCamera(index);
                    StartCameraStream(session, index, cancellationToken);
                }

                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "multi_started",
                    camera_indices = indices
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "stop":
            {
                var index = ReadInt32(message, "camera_index", 0);
                session.ActiveCameras.TryRemove(index, out _);
                StopCameraStreams(session, index);
                _cameraCaptureService.StopCamera(index);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "stopped",
                    camera_index = index
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "stop_all":
            {
                session.ActiveCameras.Clear();
                StopCameraStreams(session, null);
                _cameraCaptureService.StopAll();
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "stopped_all"
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "set_camera":
            {
                var index = ReadInt32(message, "camera_index", 0);
                session.ActiveCameras.Clear();
                StopCameraStreams(session, null);
                session.ActiveCameras[index] = true;
                _cameraCaptureService.StartCamera(index);
                StartCameraStream(session, index, cancellationToken);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "camera_changed",
                    camera_index = index,
                    camera_info = _cameraCaptureService.GetCameraInfo(index)
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
        }
    }

    private void StartMediaLoop(RemoteClientSession session, CancellationToken cancellationToken)
    {
        var loopCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        session.MediaLoopCts = loopCts;
        session.MediaLoopTask = Task.Run(async () =>
        {
            try
            {
                while (!loopCts.IsCancellationRequested && session.Socket.State == WebSocketState.Open)
                {
                    var state = await _mediaControlService.GetFullStateAsync().ConfigureAwait(false);
                    await SendEncryptedAsync(session, state, loopCts.Token).ConfigureAwait(false);
                    await Task.Delay(TimeSpan.FromSeconds(1.5), loopCts.Token).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException)
            {
                // ignored
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "Media loop stopped");
            }
        }, loopCts.Token);
    }

    private void StartScreenStream(RemoteClientSession session, int displayIndex, CancellationToken cancellationToken)
    {
        if (session.ScreenTasks.TryRemove(displayIndex, out var existing))
        {
            existing.Cancel();
            existing.Dispose();
        }

        var monitor = _screenCaptureService.GetMonitors().FirstOrDefault(display => display.Index == displayIndex) ?? _screenCaptureService.GetMonitors().First();
        var loopCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        session.ScreenTasks[displayIndex] = loopCts;

        _ = Task.Run(async () =>
        {
            try
            {
                while (!loopCts.IsCancellationRequested && session.Socket.State == WebSocketState.Open)
                {
                    var frame = _screenCaptureService.CaptureFrame(monitor, session.ScreenResolution, session.ScreenQuality);
                    if (frame.Length > 0)
                    {
                        var payload = BuildBinaryFrame(ProtocolConstants.ScreenFrameHeader, (byte)(displayIndex & 0xFF), frame);
                        await session.SendBinaryAsync(payload, loopCts.Token).ConfigureAwait(false);
                    }

                    var delay = Math.Max(1, 1000 / Math.Max(1, session.ScreenFps));
                    await Task.Delay(delay, loopCts.Token).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException)
            {
                // ignored
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "Screen stream stopped");
            }
            finally
            {
                if (session.ScreenTasks.TryRemove(displayIndex, out var removed))
                {
                    removed.Dispose();
                }
            }
        }, loopCts.Token);
    }

    private void StopScreenStreams(RemoteClientSession session, int? displayIndex)
    {
        var keys = displayIndex.HasValue
            ? session.ScreenTasks.Keys.Where(value => value == displayIndex.Value).ToArray()
            : session.ScreenTasks.Keys.ToArray();

        foreach (var key in keys)
        {
            if (session.ScreenTasks.TryRemove(key, out var cts))
            {
                cts.Cancel();
                cts.Dispose();
            }
        }
    }

    private void StartCameraStream(RemoteClientSession session, int cameraIndex, CancellationToken cancellationToken)
    {
        if (session.CameraTasks.TryRemove(cameraIndex, out var existing))
        {
            existing.Cancel();
            existing.Dispose();
        }

        var loopCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        session.CameraTasks[cameraIndex] = loopCts;

        _ = Task.Run(async () =>
        {
            try
            {
                while (!loopCts.IsCancellationRequested && session.Socket.State == WebSocketState.Open)
                {
                    var frame = CreatePlaceholderCameraFrame(cameraIndex);
                    var payload = BuildBinaryFrame(ProtocolConstants.CameraFrameHeader, (byte)(cameraIndex & 0xFF), frame);
                    await session.SendBinaryAsync(payload, loopCts.Token).ConfigureAwait(false);
                    await Task.Delay(250, loopCts.Token).ConfigureAwait(false);
                }
            }
            catch (OperationCanceledException)
            {
                // ignored
            }
            catch (Exception ex)
            {
                _logger.LogDebug(ex, "Camera stream stopped");
            }
            finally
            {
                if (session.CameraTasks.TryRemove(cameraIndex, out var removed))
                {
                    removed.Dispose();
                }
            }
        }, loopCts.Token);
    }

    private void StopCameraStreams(RemoteClientSession session, int? cameraIndex)
    {
        var keys = cameraIndex.HasValue
            ? session.CameraTasks.Keys.Where(value => value == cameraIndex.Value).ToArray()
            : session.CameraTasks.Keys.ToArray();

        foreach (var key in keys)
        {
            if (session.CameraTasks.TryRemove(key, out var cts))
            {
                cts.Cancel();
                cts.Dispose();
            }
        }
    }

    private static byte[] CreatePlaceholderCameraFrame(int cameraIndex)
    {
        using var bitmap = new Bitmap(640, 360);
        using var graphics = Graphics.FromImage(bitmap);
        graphics.Clear(Color.FromArgb(20, 22, 28));
        using var titleBrush = new SolidBrush(Color.White);
        using var bodyBrush = new SolidBrush(Color.FromArgb(190, 190, 198));
        using var titleFont = new Font("Segoe UI", 28, FontStyle.Bold);
        using var bodyFont = new Font("Segoe UI", 14);
        graphics.DrawString($"Camera {cameraIndex}", titleFont, titleBrush, 28, 118);
        graphics.DrawString("Native camera transport is connected.", bodyFont, bodyBrush, 32, 180);

        using var stream = new MemoryStream();
        bitmap.Save(stream, ImageFormat.Jpeg);
        return stream.ToArray();
    }
}
