using System;
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
                session.ScreenAudioEnabled = ReadBoolean(message, "audio_enabled", session.ScreenAudioEnabled);

                var indices = ReadIntArray(message, "display_indices");
                if (indices.Count == 0)
                {
                    indices.Add(ReadInt32(message, "display_index", 0));
                }

                foreach (var index in indices)
                {
                    StartScreenStream(session, index, cancellationToken);
                }

                if (session.ScreenAudioEnabled)
                {
                    await StartScreenAudioStreamAsync(session, cancellationToken).ConfigureAwait(false);
                }
                else
                {
                    await StopScreenAudioStreamAsync(session, sendUpdate: false, cancellationToken: cancellationToken).ConfigureAwait(false);
                }

                break;
            }
            case "stop":
            {
                var stopIndex = message.TryGetProperty("display_index", out var prop) && prop.TryGetInt32(out var index) ? (int?)index : null;
                StopScreenStreams(session, stopIndex);
                if (!stopIndex.HasValue || session.ScreenTasks.IsEmpty)
                {
                    await StopScreenAudioStreamAsync(session, sendUpdate: true, cancellationToken: cancellationToken).ConfigureAwait(false);
                }
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
            case "set_audio_enabled":
                session.ScreenAudioEnabled = ReadBoolean(message, "audio_enabled", session.ScreenAudioEnabled);
                if (session.ScreenAudioEnabled && !session.ScreenTasks.IsEmpty)
                {
                    await StartScreenAudioStreamAsync(session, cancellationToken).ConfigureAwait(false);
                }
                else
                {
                    await StopScreenAudioStreamAsync(session, sendUpdate: true, cancellationToken: cancellationToken).ConfigureAwait(false);
                }
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
                        left = display.Bounds.Left,
                        top = display.Bounds.Top,
                        is_primary = display.IsPrimary
                    }).ToArray(),
                    active_displays = session.ScreenTasks.Keys.OrderBy(value => value).ToArray(),
                    current_resolution = session.ScreenResolution,
                    current_fps = session.ScreenFps,
                    current_quality = session.ScreenQuality,
                    audio_enabled = session.ScreenAudioEnabled,
                    audio_format = session.ScreenAudioFormat is { } audioFormat
                        ? new
                        {
                            sample_rate = audioFormat.SampleRate,
                            channels = audioFormat.Channels,
                            encoding = audioFormat.Encoding,
                            bytes_per_sample = audioFormat.BytesPerSample
                        }
                        : null
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "input":
                await HandleScreenShareInputAsync(message).ConfigureAwait(false);
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
                var startResult = await _cameraCaptureService.TryStartCameraAsync(index, cancellationToken).ConfigureAwait(false);
                if (!startResult.Started)
                {
                        await SendEncryptedAsync(session, new
                        {
                            type = "camera",
                            action = "error",
                            camera_index = index,
                            code = startResult.ErrorCode,
                            message = startResult.ErrorMessage
                        }, cancellationToken).ConfigureAwait(false);
                        break;
                }

                session.ActiveCameras[index] = true;
                StartCameraStream(session, index, cancellationToken);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "started",
                    camera_index = index,
                    camera_info = _cameraCaptureService.GetCameraInfo(index, startResult.CameraName)
                }, cancellationToken).ConfigureAwait(false);
                break;
            }
            case "start_multi":
            {
                var indices = ReadIntArray(message, "camera_indices");
                var startedIndices = new System.Collections.Generic.List<int>();
                foreach (var index in indices)
                {
                    var startResult = await _cameraCaptureService.TryStartCameraAsync(index, cancellationToken).ConfigureAwait(false);
                    if (!startResult.Started)
                    {
                        await SendEncryptedAsync(session, new
                        {
                            type = "camera",
                            action = "error",
                            camera_index = index,
                            code = startResult.ErrorCode,
                            message = startResult.ErrorMessage
                        }, cancellationToken).ConfigureAwait(false);
                        continue;
                    }

                    session.ActiveCameras[index] = true;
                    startedIndices.Add(index);
                    StartCameraStream(session, index, cancellationToken);
                }

                if (startedIndices.Count > 0)
                {
                    await SendEncryptedAsync(session, new
                    {
                        type = "camera",
                        action = "multi_started",
                        camera_indices = startedIndices
                    }, cancellationToken).ConfigureAwait(false);
                }
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
                _cameraCaptureService.StopAll();
                var startResult = await _cameraCaptureService.TryStartCameraAsync(index, cancellationToken).ConfigureAwait(false);
                if (!startResult.Started)
                {
                    await SendEncryptedAsync(session, new
                    {
                        type = "camera",
                        action = "error",
                        camera_index = index,
                        code = startResult.ErrorCode,
                        message = startResult.ErrorMessage
                    }, cancellationToken).ConfigureAwait(false);
                    break;
                }

                session.ActiveCameras[index] = true;
                StartCameraStream(session, index, cancellationToken);
                await SendEncryptedAsync(session, new
                {
                    type = "camera",
                    action = "camera_changed",
                    camera_index = index,
                    camera_info = _cameraCaptureService.GetCameraInfo(index, startResult.CameraName)
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
                        await session.TrySendBinaryAsync(payload, loopCts.Token).ConfigureAwait(false);
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
                    var frame = await _cameraCaptureService.CaptureFrameAsync(cameraIndex, loopCts.Token).ConfigureAwait(false);
                    if (frame.Length == 0)
                    {
                        session.ActiveCameras.TryRemove(cameraIndex, out _);
                        var error = _cameraCaptureService.GetLastError(cameraIndex) ?? new CameraErrorInfo(
                            "frame_timeout",
                            $"Camera {cameraIndex + 1} stopped because the PC host no longer receives live frames from the webcam.");
                        _cameraCaptureService.StopCamera(cameraIndex);
                        await SendEncryptedAsync(session, new
                        {
                            type = "camera",
                            action = "error",
                            camera_index = cameraIndex,
                            code = error.Code,
                            message = error.Message
                        }, loopCts.Token).ConfigureAwait(false);
                        break;
                    }

                    var payload = BuildBinaryFrame(ProtocolConstants.CameraFrameHeader, (byte)(cameraIndex & 0xFF), frame);
                    await session.TrySendBinaryAsync(payload, loopCts.Token).ConfigureAwait(false);
                    await Task.Delay(100, loopCts.Token).ConfigureAwait(false);
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

    private async Task StartScreenAudioStreamAsync(RemoteClientSession session, CancellationToken cancellationToken)
    {
        await StopScreenAudioStreamAsync(session, sendUpdate: false, cancellationToken: cancellationToken).ConfigureAwait(false);

        var loopCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        var stream = _screenAudioCaptureService.CreateStream();
        session.ScreenAudioCts = loopCts;
        session.ScreenAudioStream = stream;

        stream.CaptureFailed += error =>
        {
            session.ScreenAudioEnabled = false;
            session.ScreenAudioFormat = null;
            _ = SendEncryptedAsync(session, new
            {
                type = "screen_share",
                action = "audio_error",
                code = error.Code,
                message = error.Message
            }, loopCts.Token);
        };

        stream.ChunkAvailable += chunk =>
        {
            if (loopCts.IsCancellationRequested || session.Socket.State != WebSocketState.Open)
            {
                return;
            }

            var payload = BuildBinaryFrame(ProtocolConstants.ScreenAudioFrameHeader, 0, chunk);
            _ = session.TrySendBinaryAsync(payload, loopCts.Token);
        };

        var startResult = stream.Start();
        if (!startResult.Started || startResult.Format is not { } format)
        {
            session.ScreenAudioEnabled = false;
            session.ScreenAudioFormat = null;
            stream.Dispose();
            session.ScreenAudioStream = null;
            session.ScreenAudioCts?.Cancel();
            session.ScreenAudioCts?.Dispose();
            session.ScreenAudioCts = null;
            await SendEncryptedAsync(session, new
            {
                type = "screen_share",
                action = "audio_error",
                code = startResult.ErrorCode ?? "audio_start_failed",
                message = startResult.ErrorMessage ?? "System audio capture could not start."
            }, cancellationToken).ConfigureAwait(false);
            return;
        }

        session.ScreenAudioEnabled = true;
        session.ScreenAudioFormat = format;
        await SendEncryptedAsync(session, new
        {
            type = "screen_share",
            action = "audio_format",
            sample_rate = format.SampleRate,
            channels = format.Channels,
            encoding = format.Encoding,
            bytes_per_sample = format.BytesPerSample
        }, cancellationToken).ConfigureAwait(false);
    }

    private async Task StopScreenAudioStreamAsync(RemoteClientSession session, bool sendUpdate, CancellationToken cancellationToken)
    {
        session.ScreenAudioEnabled = false;
        session.ScreenAudioFormat = null;

        if (session.ScreenAudioCts is not null)
        {
            session.ScreenAudioCts.Cancel();
            session.ScreenAudioCts.Dispose();
            session.ScreenAudioCts = null;
        }

        session.ScreenAudioStream?.Dispose();
        session.ScreenAudioStream = null;

        if (sendUpdate && session.Socket.State == WebSocketState.Open)
        {
            await SendEncryptedAsync(session, new
            {
                type = "screen_share",
                action = "audio_stopped"
            }, cancellationToken).ConfigureAwait(false);
        }
    }

    private Task HandleScreenShareInputAsync(JsonElement message)
    {
        var monitors = _screenCaptureService.GetMonitors();
        var monitorIndex = ReadInt32(message, "monitor_index", 0);
        var monitor = monitors.FirstOrDefault(display => display.Index == monitorIndex) ?? monitors.FirstOrDefault();
        if (monitor is null)
        {
            return Task.CompletedTask;
        }

        var x = ResolveScreenCoordinate(message, "normalized_x", "x", monitor.Bounds.Left, monitor.Bounds.Width);
        var y = ResolveScreenCoordinate(message, "normalized_y", "y", monitor.Bounds.Top, monitor.Bounds.Height);
        var inputAction = GetString(message, "input_action", GetString(message, "action")).ToLowerInvariant();
        var button = GetString(message, "button", "left");

        switch (inputAction)
        {
            case "move":
                _inputService.MovePointerAbsolute(x, y);
                break;
            case "press":
                _inputService.MouseDownAt(x, y, button);
                break;
            case "release":
                _inputService.MouseUpAt(x, y, button);
                break;
            case "click":
                _inputService.ClickAt(x, y, button, Math.Max(1, ReadInt32(message, "count", 1)));
                break;
            case "scroll":
                _inputService.ScrollAt(
                    x,
                    y,
                    ReadInt32(message, "wheel_dx", ReadInt32(message, "dx", 0)),
                    ReadInt32(message, "wheel_dy", ReadInt32(message, "dy", 0)));
                break;
        }

        return Task.CompletedTask;
    }

    private static int ResolveScreenCoordinate(JsonElement message, string normalizedProperty, string fallbackProperty, int offset, int size)
    {
        if (message.TryGetProperty(normalizedProperty, out var normalizedProp) && normalizedProp.TryGetDouble(out var normalized))
        {
            var clamped = Math.Clamp(normalized, 0, 1);
            return offset + (int)Math.Round(clamped * Math.Max(0, size - 1));
        }

        return offset + Math.Clamp(ReadInt32(message, fallbackProperty, 0), 0, Math.Max(0, size - 1));
    }
}
