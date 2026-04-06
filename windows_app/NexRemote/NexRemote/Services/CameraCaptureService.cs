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
using Windows.Media.MediaProperties;
using Windows.Media;
using Windows.Storage.Streams;

namespace NexRemote.Services;

internal sealed class CameraCaptureService
{
    private readonly ConcurrentDictionary<int, bool> _activeCameras = new();
    private readonly ConcurrentDictionary<int, CameraSession> _sessions = new();
    private readonly SemaphoreSlim _deviceGate = new(1, 1);
    private IReadOnlyList<DeviceInformation>? _deviceCache;

    public async Task<IReadOnlyList<object>> GetCamerasAsync()
    {
        var devices = await GetDeviceCacheAsync().ConfigureAwait(false);
        return devices
            .Select((device, index) => (object)new
            {
                index,
                name = device.Name,
                id = device.Id,
                available = true,
                active = _activeCameras.ContainsKey(index)
            })
            .ToList();
    }

    public object GetCameraInfo(int cameraIndex, string? cameraName = null)
    {
        var devices = _deviceCache ?? Array.Empty<DeviceInformation>();
        var name = cameraName;
        if (string.IsNullOrWhiteSpace(name) && cameraIndex >= 0 && cameraIndex < devices.Count)
        {
            name = devices[cameraIndex].Name;
        }

        return new
        {
            index = cameraIndex,
            name = name ?? $"Camera {cameraIndex}",
            available = true,
            active = _activeCameras.ContainsKey(cameraIndex)
        };
    }

    public void StartCamera(int cameraIndex)
    {
        _activeCameras[cameraIndex] = true;
    }

    public void StopCamera(int cameraIndex)
    {
        _activeCameras.TryRemove(cameraIndex, out _);
        if (_sessions.TryRemove(cameraIndex, out var session))
        {
            _ = session.DisposeAsync();
        }
    }

    public void StopAll()
    {
        _activeCameras.Clear();
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
        if (!_activeCameras.ContainsKey(cameraIndex))
        {
            return Array.Empty<byte>();
        }

        var session = await GetOrCreateSessionAsync(cameraIndex, cancellationToken).ConfigureAwait(false);
        if (session is null)
        {
            return Array.Empty<byte>();
        }

        await session.Gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            using var frame = new VideoFrame(BitmapPixelFormat.Bgra8, 640, 360);
            using var previewFrame = await session.Capture.GetPreviewFrameAsync(frame).AsTask(cancellationToken).ConfigureAwait(false);
            var softwareBitmap = previewFrame.SoftwareBitmap;
            if (softwareBitmap is null)
            {
                return Array.Empty<byte>();
            }

            using var converted = SoftwareBitmap.Convert(
                softwareBitmap,
                BitmapPixelFormat.Bgra8,
                BitmapAlphaMode.Premultiplied);
            using var stream = new InMemoryRandomAccessStream();
            var encoder = await BitmapEncoder.CreateAsync(BitmapEncoder.JpegEncoderId, stream).AsTask(cancellationToken).ConfigureAwait(false);
            encoder.SetSoftwareBitmap(converted);
            encoder.IsThumbnailGenerated = false;
            await encoder.FlushAsync().AsTask(cancellationToken).ConfigureAwait(false);
            stream.Seek(0);
            var size = checked((int)stream.Size);
            var bytes = new byte[size];
            await stream.ReadAsync(bytes.AsBuffer(), (uint)size, InputStreamOptions.None).AsTask(cancellationToken).ConfigureAwait(false);
            return bytes;
        }
        catch
        {
            return Array.Empty<byte>();
        }
        finally
        {
            session.Gate.Release();
        }
    }

    private async Task<IReadOnlyList<DeviceInformation>> GetDeviceCacheAsync()
    {
        await _deviceGate.WaitAsync().ConfigureAwait(false);
        try
        {
            _deviceCache ??= await DeviceInformation.FindAllAsync(DeviceClass.VideoCapture);
            return _deviceCache;
        }
        catch
        {
            return Array.Empty<DeviceInformation>();
        }
        finally
        {
            _deviceGate.Release();
        }
    }

    private async Task<CameraSession?> GetOrCreateSessionAsync(int cameraIndex, CancellationToken cancellationToken)
    {
        if (_sessions.TryGetValue(cameraIndex, out var existing))
        {
            return existing;
        }

        var devices = await GetDeviceCacheAsync().ConfigureAwait(false);
        if (cameraIndex < 0 || cameraIndex >= devices.Count)
        {
            return null;
        }

        var capture = new MediaCapture();
        try
        {
            await capture.InitializeAsync(new MediaCaptureInitializationSettings
            {
                VideoDeviceId = devices[cameraIndex].Id,
                StreamingCaptureMode = StreamingCaptureMode.Video,
                MemoryPreference = MediaCaptureMemoryPreference.Cpu,
                SharingMode = MediaCaptureSharingMode.SharedReadOnly
            }).AsTask(cancellationToken).ConfigureAwait(false);
            await ApplyPreferredPreviewFormatAsync(capture, cancellationToken).ConfigureAwait(false);
            await capture.StartPreviewAsync().AsTask(cancellationToken).ConfigureAwait(false);
        }
        catch
        {
            capture.Dispose();
            return null;
        }

        var session = new CameraSession(capture);
        if (_sessions.TryAdd(cameraIndex, session))
        {
            return session;
        }

        await session.DisposeAsync().ConfigureAwait(false);
        return _sessions.TryGetValue(cameraIndex, out var raceWinner) ? raceWinner : null;
    }

    private static async Task ApplyPreferredPreviewFormatAsync(MediaCapture capture, CancellationToken cancellationToken)
    {
        try
        {
            var properties = capture.VideoDeviceController.GetAvailableMediaStreamProperties(MediaStreamType.VideoPreview);

            var preferred = properties
                .OfType<VideoEncodingProperties>()
                .Where(item => item.Width > 0 && item.Height > 0)
                .OrderByDescending(item => item.Width * item.Height)
                .FirstOrDefault(item => item.Width <= 1280 && item.Height <= 720)
                ?? properties.OfType<VideoEncodingProperties>().FirstOrDefault();

            if (preferred is not null)
            {
                await capture.VideoDeviceController
                    .SetMediaStreamPropertiesAsync(MediaStreamType.VideoPreview, preferred)
                    .AsTask(cancellationToken)
                    .ConfigureAwait(false);
            }
        }
        catch
        {
            // Keep the default preview format if the device rejects changes.
        }
    }

    private sealed class CameraSession : IAsyncDisposable
    {
        public CameraSession(MediaCapture capture)
        {
            Capture = capture;
        }

        public MediaCapture Capture { get; }
        public SemaphoreSlim Gate { get; } = new(1, 1);

        public ValueTask DisposeAsync()
        {
            Gate.Dispose();
            return new ValueTask(DisposeCoreAsync());
        }

        private async Task DisposeCoreAsync()
        {
            try
            {
                await Capture.StopPreviewAsync().AsTask().ConfigureAwait(false);
            }
            catch
            {
                // ignored
            }

            Capture.Dispose();
        }
    }
}
