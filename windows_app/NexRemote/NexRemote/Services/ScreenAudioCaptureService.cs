using System;
using NAudio.Wave;
using Serilog;

namespace NexRemote.Services;

internal readonly record struct ScreenAudioFormatInfo(int SampleRate, int Channels, string Encoding, int BytesPerSample);

internal readonly record struct ScreenAudioErrorInfo(string Code, string Message);

internal readonly record struct ScreenAudioStartResult(bool Started, ScreenAudioFormatInfo? Format, string? ErrorCode, string? ErrorMessage)
{
    public static ScreenAudioStartResult Success(ScreenAudioFormatInfo format) => new(true, format, null, null);

    public static ScreenAudioStartResult Failure(string errorCode, string errorMessage)
        => new(false, null, errorCode, errorMessage);
}

internal sealed class ScreenAudioCaptureService
{
    public bool IsSupported => TryGetAvailability(out _);

    public bool TryGetAvailability(out string? reason)
    {
        try
        {
            using var capture = new WasapiLoopbackCapture();
            var _ = capture.WaveFormat;
            reason = null;
            return true;
        }
        catch (Exception ex)
        {
            reason = ex.Message;
            return false;
        }
    }

    public ScreenAudioCaptureStream CreateStream() => new();

    internal sealed class ScreenAudioCaptureStream : IDisposable
    {
        private readonly object _stateGate = new();
        private WasapiLoopbackCapture? _capture;
        private ScreenAudioFormatInfo? _format;
        private ScreenAudioErrorInfo? _lastError;
        private bool _disposed;

        public event Action<byte[]>? ChunkAvailable;
        public event Action<ScreenAudioErrorInfo>? CaptureFailed;

        public ScreenAudioFormatInfo? Format
        {
            get
            {
                lock (_stateGate)
                {
                    return _format;
                }
            }
        }

        public ScreenAudioErrorInfo? LastError
        {
            get
            {
                lock (_stateGate)
                {
                    return _lastError;
                }
            }
        }

        public ScreenAudioStartResult Start()
        {
            lock (_stateGate)
            {
                ThrowIfDisposed();
                if (_capture is not null)
                {
                    return _format is { } existingFormat
                        ? ScreenAudioStartResult.Success(existingFormat)
                        : ScreenAudioStartResult.Failure("audio_start_failed", "System audio capture is already running.");
                }

                try
                {
                    var capture = new WasapiLoopbackCapture();
                    capture.DataAvailable += OnDataAvailable;
                    capture.RecordingStopped += OnRecordingStopped;
                    capture.StartRecording();

                    _capture = capture;
                    _format = CreateOutputFormat(capture.WaveFormat);
                    _lastError = null;
                    return ScreenAudioStartResult.Success(_format.Value);
                }
                catch (Exception ex)
                {
                    _lastError = new ScreenAudioErrorInfo("audio_start_failed", $"System audio capture could not start: {ex.Message}");
                    Log.Warning(ex, "Failed to start system audio loopback capture.");
                    CaptureFailed?.Invoke(_lastError.Value);
                    return ScreenAudioStartResult.Failure(_lastError.Value.Code, _lastError.Value.Message);
                }
            }
        }

        public void Stop()
        {
            WasapiLoopbackCapture? capture = null;
            lock (_stateGate)
            {
                if (_capture is null)
                {
                    return;
                }

                capture = _capture;
                _capture = null;
                _format = null;
            }

            capture.DataAvailable -= OnDataAvailable;
            capture.RecordingStopped -= OnRecordingStopped;
            try
            {
                capture.StopRecording();
            }
            catch
            {
                // ignored
            }

            capture.Dispose();
        }

        public void Dispose()
        {
            lock (_stateGate)
            {
                if (_disposed)
                {
                    return;
                }

                _disposed = true;
            }

            Stop();
        }

        private void OnDataAvailable(object? sender, WaveInEventArgs e)
        {
            try
            {
                var capture = _capture;
                var format = _format;
                if (capture is null || format is null || e.BytesRecorded <= 0)
                {
                    return;
                }

                var payload = ConvertToPcm16(capture.WaveFormat, format.Value, e.Buffer, e.BytesRecorded);
                if (payload.Length > 0)
                {
                    ChunkAvailable?.Invoke(payload);
                }
            }
            catch (Exception ex)
            {
                lock (_stateGate)
                {
                    _lastError = new ScreenAudioErrorInfo("audio_capture_failed", $"System audio capture failed: {ex.Message}");
                }

                Log.Warning(ex, "System audio loopback capture failed while handling a chunk.");
                CaptureFailed?.Invoke(_lastError.Value);
            }
        }

        private void OnRecordingStopped(object? sender, StoppedEventArgs e)
        {
            if (e.Exception is null)
            {
                return;
            }

            lock (_stateGate)
            {
                _lastError = new ScreenAudioErrorInfo("audio_capture_failed", $"System audio capture stopped: {e.Exception.Message}");
            }

            Log.Warning(e.Exception, "System audio loopback capture stopped unexpectedly.");
            CaptureFailed?.Invoke(_lastError.Value);
        }

        private static ScreenAudioFormatInfo CreateOutputFormat(WaveFormat inputFormat)
        {
            var channels = Math.Clamp(inputFormat.Channels, 1, 2);
            return new ScreenAudioFormatInfo(
                inputFormat.SampleRate,
                channels,
                "pcm16",
                2);
        }

        private static byte[] ConvertToPcm16(WaveFormat inputFormat, ScreenAudioFormatInfo outputFormat, byte[] buffer, int bytesRecorded)
        {
            var inputChannels = Math.Max(1, inputFormat.Channels);
            var outputChannels = Math.Max(1, outputFormat.Channels);
            var bytesPerSample = Math.Max(1, inputFormat.BitsPerSample / 8);
            var frameSize = inputChannels * bytesPerSample;
            if (frameSize <= 0 || bytesRecorded < frameSize)
            {
                return Array.Empty<byte>();
            }

            var frameCount = bytesRecorded / frameSize;
            var output = new byte[frameCount * outputChannels * outputFormat.BytesPerSample];

            for (var frameIndex = 0; frameIndex < frameCount; frameIndex++)
            {
                for (var channelIndex = 0; channelIndex < outputChannels; channelIndex++)
                {
                    var sampleOffset = frameIndex * frameSize + Math.Min(channelIndex, inputChannels - 1) * bytesPerSample;
                    short sample = inputFormat.Encoding switch
                    {
                        WaveFormatEncoding.IeeeFloat when inputFormat.BitsPerSample == 32
                            => FloatToInt16(BitConverter.ToSingle(buffer, sampleOffset)),
                        WaveFormatEncoding.Pcm when inputFormat.BitsPerSample == 16
                            => BitConverter.ToInt16(buffer, sampleOffset),
                        WaveFormatEncoding.Pcm when inputFormat.BitsPerSample == 32
                            => Int32ToInt16(BitConverter.ToInt32(buffer, sampleOffset)),
                        _ => 0
                    };

                    var outputOffset = (frameIndex * outputChannels + channelIndex) * outputFormat.BytesPerSample;
                    output[outputOffset] = (byte)(sample & 0xFF);
                    output[outputOffset + 1] = (byte)((sample >> 8) & 0xFF);
                }
            }

            return output;
        }

        private static short FloatToInt16(float sample)
        {
            var clamped = Math.Clamp(sample, -1f, 1f);
            return (short)Math.Round(clamped * short.MaxValue);
        }

        private static short Int32ToInt16(int sample)
        {
            var scaled = sample / 65536.0;
            return (short)Math.Clamp(Math.Round(scaled), short.MinValue, short.MaxValue);
        }

        private void ThrowIfDisposed()
        {
            if (_disposed)
            {
                throw new ObjectDisposedException(nameof(ScreenAudioCaptureStream));
            }
        }
    }
}
