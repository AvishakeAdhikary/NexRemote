using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Threading;
using System.Threading.Tasks;
using Windows.Devices.Enumeration;
using Windows.Graphics.Imaging;
using Windows.Media.Capture;
using Windows.Media.Capture.Frames;
using Windows.Media.MediaProperties;
using Windows.Storage.Streams;
using Serilog;

namespace NexRemote.Services;

internal readonly record struct CameraErrorInfo(string Code, string Message);

internal readonly record struct CameraStartResult(bool Started, int CameraIndex, string CameraName, string? ErrorCode, string? ErrorMessage)
{
    public static CameraStartResult Success(int cameraIndex, string cameraName) => new(true, cameraIndex, cameraName, null, null);

    public static CameraStartResult Failure(int cameraIndex, string cameraName, string errorCode, string errorMessage)
        => new(false, cameraIndex, cameraName, errorCode, errorMessage);
}

internal sealed record CameraDescriptor(int Index, string Id, string Name, MediaFrameSourceGroup? SourceGroup);

internal sealed class CameraCaptureService
{
    private static readonly TimeSpan FirstFrameTimeout = TimeSpan.FromSeconds(4);
    private readonly ConcurrentDictionary<string, bool> _activeCameraIds = new(StringComparer.OrdinalIgnoreCase);
    private readonly ConcurrentDictionary<string, CameraSession> _sessions = new(StringComparer.OrdinalIgnoreCase);
    private readonly SemaphoreSlim _deviceGate = new(1, 1);
    private IReadOnlyList<CameraDescriptor> _cameraCache = Array.Empty<CameraDescriptor>();

    public async Task<IReadOnlyList<object>> GetCamerasAsync()
    {
        var cameras = await RefreshCameraCacheAsync().ConfigureAwait(false);
        return cameras
            .Select(camera => (object)new
            {
                index = camera.Index,
                name = camera.Name,
                id = camera.Id,
                available = true,
                active = _activeCameraIds.ContainsKey(camera.Id)
            })
            .ToList();
    }

    public object GetCameraInfo(int cameraIndex, string? cameraName = null)
    {
        var descriptor = ResolveDescriptor(cameraIndex);
        var resolvedName = cameraName
            ?? descriptor?.Name
            ?? $"Camera {cameraIndex + 1}";
        return new
        {
            index = cameraIndex,
            name = resolvedName,
            available = descriptor is not null,
            active = descriptor is not null && _activeCameraIds.ContainsKey(descriptor.Id)
        };
    }

    public async Task<CameraStartResult> TryStartCameraAsync(int cameraIndex, CancellationToken cancellationToken = default)
    {
        var cameras = await RefreshCameraCacheAsync().ConfigureAwait(false);
        var descriptor = cameras.FirstOrDefault(camera => camera.Index == cameraIndex);
        if (descriptor is null)
        {
            return CameraStartResult.Failure(
                cameraIndex,
                $"Camera {cameraIndex + 1}",
                "device_missing",
                "The selected camera is no longer available on the PC host.");
        }

        try
        {
            var session = await GetOrCreateSessionAsync(descriptor, cancellationToken).ConfigureAwait(false);
            var started = await session.WaitForFirstFrameAsync(FirstFrameTimeout, cancellationToken).ConfigureAwait(false);
            if (!started)
            {
                var error = session.GetLastError() ?? new CameraErrorInfo(
                    "frame_timeout",
                    $"{descriptor.Name} did not deliver a video frame in time. Check whether another app is locking the webcam.");
                StopCamera(cameraIndex);
                return CameraStartResult.Failure(cameraIndex, descriptor.Name, error.Code, error.Message);
            }

            _activeCameraIds[descriptor.Id] = true;
            return CameraStartResult.Success(cameraIndex, descriptor.Name);
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (CameraServiceException ex)
        {
            Log.Warning(ex, "Camera {CameraIndex} ({CameraName}) failed to start.", cameraIndex, descriptor.Name);
            StopCamera(cameraIndex);
            return CameraStartResult.Failure(cameraIndex, descriptor.Name, ex.Code, ex.Message);
        }
        catch (UnauthorizedAccessException ex)
        {
            Log.Warning(ex, "Camera {CameraIndex} ({CameraName}) access was denied.", cameraIndex, descriptor.Name);
            StopCamera(cameraIndex);
            return CameraStartResult.Failure(
                cameraIndex,
                descriptor.Name,
                "access_denied",
                "Windows denied access to the selected webcam. Check privacy settings and close any app that is exclusively using the camera.");
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Camera {CameraIndex} ({CameraName}) failed during startup validation.", cameraIndex, descriptor.Name);
            StopCamera(cameraIndex);
            return CameraStartResult.Failure(
                cameraIndex,
                descriptor.Name,
                "initialize_failed",
                $"NexRemote could not initialize {descriptor.Name}: {ex.Message}");
        }
    }

    public void StopCamera(int cameraIndex)
    {
        var descriptor = ResolveDescriptor(cameraIndex);
        if (descriptor is null)
        {
            return;
        }

        _activeCameraIds.TryRemove(descriptor.Id, out _);
        if (_sessions.TryRemove(descriptor.Id, out var session))
        {
            _ = session.DisposeAsync();
        }
    }

    public void StopAll()
    {
        _activeCameraIds.Clear();
        foreach (var pair in _sessions.ToArray())
        {
            if (_sessions.TryRemove(pair.Key, out var session))
            {
                _ = session.DisposeAsync();
            }
        }
    }

    public async Task<byte[]> CaptureFrameAsync(int cameraIndex, CancellationToken cancellationToken = default)
    {
        var descriptor = ResolveDescriptor(cameraIndex);
        if (descriptor is null || !_activeCameraIds.ContainsKey(descriptor.Id))
        {
            return Array.Empty<byte>();
        }

        if (!_sessions.TryGetValue(descriptor.Id, out var session))
        {
            session = await GetOrCreateSessionAsync(descriptor, cancellationToken).ConfigureAwait(false);
        }

        return session?.GetLatestFrame() ?? Array.Empty<byte>();
    }

    public CameraErrorInfo? GetLastError(int cameraIndex)
    {
        var descriptor = ResolveDescriptor(cameraIndex);
        if (descriptor is null || !_sessions.TryGetValue(descriptor.Id, out var session))
        {
            return null;
        }

        return session.GetLastError();
    }

    private CameraDescriptor? ResolveDescriptor(int cameraIndex)
        => _cameraCache.FirstOrDefault(camera => camera.Index == cameraIndex);

    private async Task<IReadOnlyList<CameraDescriptor>> RefreshCameraCacheAsync()
    {
        await _deviceGate.WaitAsync().ConfigureAwait(false);
        try
        {
            var devices = await DeviceInformation.FindAllAsync(DeviceClass.VideoCapture);
            IReadOnlyList<MediaFrameSourceGroup> groups;
            try
            {
                groups = await MediaFrameSourceGroup.FindAllAsync();
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Failed to enumerate media frame source groups for cameras.");
                groups = Array.Empty<MediaFrameSourceGroup>();
            }

            _cameraCache = devices
                .Select((device, index) => new CameraDescriptor(index, device.Id, device.Name, FindSourceGroup(groups, device.Id)))
                .ToList();

            return _cameraCache;
        }
        catch (Exception ex)
        {
            Log.Warning(ex, "Failed to enumerate video capture devices.");
            _cameraCache = Array.Empty<CameraDescriptor>();
            return _cameraCache;
        }
        finally
        {
            _deviceGate.Release();
        }
    }

    private async Task<CameraSession> GetOrCreateSessionAsync(CameraDescriptor descriptor, CancellationToken cancellationToken)
    {
        if (_sessions.TryGetValue(descriptor.Id, out var existing))
        {
            return existing;
        }

        var capture = new MediaCapture();
        try
        {
            var initialization = new MediaCaptureInitializationSettings
            {
                StreamingCaptureMode = StreamingCaptureMode.Video,
                MemoryPreference = MediaCaptureMemoryPreference.Cpu,
                SharingMode = MediaCaptureSharingMode.SharedReadOnly
            };

            if (descriptor.SourceGroup is not null)
            {
                initialization.SourceGroup = descriptor.SourceGroup;
            }
            else
            {
                initialization.VideoDeviceId = descriptor.Id;
            }

            await capture.InitializeAsync(initialization).AsTask(cancellationToken).ConfigureAwait(false);
            var source = SelectColorSource(capture);
            if (source is null)
            {
                throw new CameraServiceException(
                    "initialize_failed",
                    $"{descriptor.Name} does not expose a usable color video source for frame capture.");
            }

            await ApplyPreferredFormatAsync(source, cancellationToken).ConfigureAwait(false);
            var reader = await capture.CreateFrameReaderAsync(source, MediaEncodingSubtypes.Bgra8)
                .AsTask(cancellationToken)
                .ConfigureAwait(false);
            var session = new CameraSession(descriptor, capture, reader);

            capture.Failed += session.OnCaptureFailed;
            reader.FrameArrived += session.OnFrameArrived;

            var startStatus = await reader.StartAsync().AsTask(cancellationToken).ConfigureAwait(false);
            if (startStatus != MediaFrameReaderStartStatus.Success)
            {
                capture.Failed -= session.OnCaptureFailed;
                reader.FrameArrived -= session.OnFrameArrived;
                await session.DisposeAsync().ConfigureAwait(false);
                throw new CameraServiceException(
                    "reader_start_failed",
                    $"{descriptor.Name} could not start its camera frame reader ({startStatus}).");
            }

            if (_sessions.TryAdd(descriptor.Id, session))
            {
                return session;
            }

            capture.Failed -= session.OnCaptureFailed;
            reader.FrameArrived -= session.OnFrameArrived;
            await session.DisposeAsync().ConfigureAwait(false);
            return _sessions[descriptor.Id];
        }
        catch (OperationCanceledException)
        {
            capture.Dispose();
            throw;
        }
        catch (UnauthorizedAccessException)
        {
            capture.Dispose();
            throw;
        }
        catch
        {
            capture.Dispose();
            throw;
        }
    }

    private static MediaFrameSource? SelectColorSource(MediaCapture capture)
    {
        return capture.FrameSources.Values
            .Where(source => source.Info.SourceKind == MediaFrameSourceKind.Color)
            .OrderBy(source => source.Info.MediaStreamType == MediaStreamType.VideoPreview ? 0 : 1)
            .FirstOrDefault();
    }

    private static async Task ApplyPreferredFormatAsync(MediaFrameSource source, CancellationToken cancellationToken)
    {
        try
        {
            var preferredFormat = source.SupportedFormats
                .Where(format => format.VideoFormat is not null && format.VideoFormat.Width > 0 && format.VideoFormat.Height > 0)
                .OrderBy(format =>
                {
                    var width = format.VideoFormat?.Width ?? int.MaxValue;
                    var height = format.VideoFormat?.Height ?? int.MaxValue;
                    var score = Math.Abs(width - 1280) + Math.Abs(height - 720);
                    return score;
                })
                .FirstOrDefault();

            if (preferredFormat is not null)
            {
                await source.SetFormatAsync(preferredFormat).AsTask(cancellationToken).ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            Log.Debug(ex, "Camera frame source rejected the preferred capture format; using the default format instead.");
        }
    }

    private static MediaFrameSourceGroup? FindSourceGroup(IEnumerable<MediaFrameSourceGroup> groups, string deviceId)
    {
        return groups.FirstOrDefault(group => group.SourceInfos.Any(sourceInfo =>
            sourceInfo.SourceKind == MediaFrameSourceKind.Color &&
            string.Equals(sourceInfo.DeviceInformation?.Id, deviceId, StringComparison.OrdinalIgnoreCase)));
    }

    private sealed class CameraSession : IAsyncDisposable
    {
        private readonly object _frameGate = new();
        private readonly TaskCompletionSource<bool> _firstFrameReceived = new(TaskCreationOptions.RunContinuationsAsynchronously);
        private readonly CameraDescriptor _descriptor;
        private byte[] _latestFrame = Array.Empty<byte>();
        private DateTimeOffset _lastFrameAt = DateTimeOffset.MinValue;
        private CameraErrorInfo? _lastError;
        private bool _disposed;

        public CameraSession(CameraDescriptor descriptor, MediaCapture capture, MediaFrameReader reader)
        {
            _descriptor = descriptor;
            Capture = capture;
            Reader = reader;
        }

        public MediaCapture Capture { get; }
        public MediaFrameReader Reader { get; }

        public async Task<bool> WaitForFirstFrameAsync(TimeSpan timeout, CancellationToken cancellationToken)
        {
            using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeoutCts.CancelAfter(timeout);

            try
            {
                return await _firstFrameReceived.Task.WaitAsync(timeoutCts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
            {
                SetError(
                    "frame_timeout",
                    $"{_descriptor.Name} did not deliver a video frame in time. Check whether another app is exclusively using the webcam.");
                return false;
            }
        }

        public byte[] GetLatestFrame()
        {
            lock (_frameGate)
            {
                if (_lastError is not null)
                {
                    return Array.Empty<byte>();
                }

                if (_latestFrame.Length == 0)
                {
                    return Array.Empty<byte>();
                }

                if (DateTimeOffset.UtcNow - _lastFrameAt > TimeSpan.FromSeconds(5))
                {
                    _lastError = new CameraErrorInfo(
                        "frame_timeout",
                        $"{_descriptor.Name} stopped producing video frames.");
                    return Array.Empty<byte>();
                }

                return _latestFrame;
            }
        }

        public CameraErrorInfo? GetLastError()
        {
            lock (_frameGate)
            {
                return _lastError;
            }
        }

        public void OnFrameArrived(MediaFrameReader sender, MediaFrameArrivedEventArgs args)
        {
            if (_disposed)
            {
                return;
            }

            try
            {
                using var frameReference = sender.TryAcquireLatestFrame();
                var softwareBitmap = frameReference?.VideoMediaFrame?.SoftwareBitmap;
                if (softwareBitmap is null)
                {
                    return;
                }

                var encoded = EncodeFrame(softwareBitmap);
                if (encoded.Length == 0)
                {
                    return;
                }

                lock (_frameGate)
                {
                    _latestFrame = encoded;
                    _lastFrameAt = DateTimeOffset.UtcNow;
                    _lastError = null;
                }

                _firstFrameReceived.TrySetResult(true);
            }
            catch (Exception ex)
            {
                Log.Warning(ex, "Camera frame encoding failed for {CameraName}.", _descriptor.Name);
                SetError(
                    "frame_encode_failed",
                    $"{_descriptor.Name} produced a frame that NexRemote could not encode for streaming.");
            }
        }

        public void OnCaptureFailed(MediaCapture sender, MediaCaptureFailedEventArgs errorEventArgs)
        {
            var message = string.IsNullOrWhiteSpace(errorEventArgs.Message)
                ? $"{_descriptor.Name} stopped responding."
                : errorEventArgs.Message;
            SetError("device_lost", $"{_descriptor.Name} disconnected or stopped responding: {message}");
        }

        public async ValueTask DisposeAsync()
        {
            if (_disposed)
            {
                return;
            }

            _disposed = true;
            Reader.FrameArrived -= OnFrameArrived;
            Capture.Failed -= OnCaptureFailed;

            try
            {
                await Reader.StopAsync().AsTask().ConfigureAwait(false);
            }
            catch
            {
                // ignored
            }

            Reader.Dispose();
            Capture.Dispose();
        }

        private void SetError(string code, string message)
        {
            lock (_frameGate)
            {
                _lastError = new CameraErrorInfo(code, message);
            }

            _firstFrameReceived.TrySetResult(false);
        }

        private static byte[] EncodeFrame(SoftwareBitmap softwareBitmap)
        {
            using var converted = SoftwareBitmap.Convert(
                softwareBitmap,
                BitmapPixelFormat.Bgra8,
                BitmapAlphaMode.Ignore);
            using var stream = new InMemoryRandomAccessStream();
            var encoder = BitmapEncoder.CreateAsync(BitmapEncoder.JpegEncoderId, stream).AsTask().GetAwaiter().GetResult();
            encoder.SetSoftwareBitmap(converted);
            encoder.IsThumbnailGenerated = false;
            encoder.FlushAsync().AsTask().GetAwaiter().GetResult();
            stream.Seek(0);
            var size = checked((int)stream.Size);
            var bytes = new byte[size];
            stream.ReadAsync(bytes.AsBuffer(), (uint)size, InputStreamOptions.None).AsTask().GetAwaiter().GetResult();
            return bytes;
        }
    }

    private sealed class CameraServiceException : Exception
    {
        public CameraServiceException(string code, string message)
            : base(message)
        {
            Code = code;
        }

        public string Code { get; }
    }
}
