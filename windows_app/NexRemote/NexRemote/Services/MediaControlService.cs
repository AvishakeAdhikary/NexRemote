using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Text.Json;
using System.Threading.Tasks;
using Windows.Media.Control;

namespace NexRemote.Services;

internal sealed class MediaControlService
{
    private const int VkMediaPlayPause = 0xB3;
    private const int VkMediaStop = 0xB2;
    private const int VkMediaNextTrack = 0xB0;
    private const int VkMediaPrevTrack = 0xB1;
    private const int VkVolumeMute = 0xAD;
    private const int VkVolumeDown = 0xAE;
    private const int VkVolumeUp = 0xAF;

    public async Task<object?> HandleRequestAsync(JsonElement data)
    {
        var action = GetString(data, "action");
        try
        {
            switch (action)
            {
                case "play":
                case "pause":
                    SendMediaKey(VkMediaPlayPause);
                    return null;
                case "stop":
                    SendMediaKey(VkMediaStop);
                    return null;
                case "next":
                    SendMediaKey(VkMediaNextTrack);
                    return null;
                case "previous":
                    SendMediaKey(VkMediaPrevTrack);
                    return null;
                case "volume":
                    SetVolume(ReadInt32(data, "value", 50));
                    return null;
                case "mute_toggle":
                    ToggleMute();
                    return null;
                case "volume_up":
                    SendMediaKey(VkVolumeUp);
                    return null;
                case "volume_down":
                    SendMediaKey(VkVolumeDown);
                    return null;
                case "seek":
                    return null;
                case "get_info":
                    return await GetFullStateAsync().ConfigureAwait(false);
                default:
                    return null;
            }
        }
        catch
        {
            return null;
        }
    }

    public async Task<object> GetFullStateAsync()
    {
        var volume = -1;
        var isMuted = false;

        try
        {
            (volume, isMuted) = GetVolumeState();
        }
        catch
        {
            // fall back to placeholders
        }

        var title = string.Empty;
        var artist = string.Empty;
        var isPlaying = false;
        var hasMedia = false;

        try
        {
            var manager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync().AsTask().ConfigureAwait(false);
            var session = manager.GetCurrentSession();
            if (session is not null)
            {
                var playback = session.GetPlaybackInfo();
                hasMedia = playback is not null;
                isPlaying = playback?.PlaybackStatus == GlobalSystemMediaTransportControlsSessionPlaybackStatus.Playing;

                var properties = await session.TryGetMediaPropertiesAsync().AsTask().ConfigureAwait(false);
                title = properties.Title ?? string.Empty;
                artist = properties.Artist ?? string.Empty;
            }
        }
        catch
        {
            // fall back below
        }

        if (string.IsNullOrWhiteSpace(title))
        {
            title = hasMedia ? "Now Playing" : "No Media Playing";
        }

        return new
        {
            type = "media_control",
            action = "media_info",
            volume,
            is_muted = isMuted,
            title,
            artist,
            is_playing = isPlaying,
            has_media = hasMedia,
            position = 0,
            duration = 0
        };
    }

    private static void SendMediaKey(int vk)
    {
        keybd_event((byte)vk, 0, 0, IntPtr.Zero);
        keybd_event((byte)vk, 0, 2, IntPtr.Zero);
    }

    private static void ToggleMute()
    {
        try
        {
            var volume = GetEndpointVolume();
            if (volume is not null)
            {
                volume.GetMute(out var mute);
                volume.SetMute(!mute, Guid.Empty);
                return;
            }
        }
        catch
        {
            // fall back below
        }

        SendMediaKey(VkVolumeMute);
    }

    private static void SetVolume(int volume)
    {
        volume = Math.Clamp(volume, 0, 100);
        try
        {
            var endpoint = GetEndpointVolume();
            if (endpoint is not null)
            {
                endpoint.SetMasterVolumeLevelScalar(volume / 100.0f, Guid.Empty);
                return;
            }
        }
        catch
        {
            // fall back below
        }

        SendMediaKey(volume > 50 ? VkVolumeUp : VkVolumeDown);
    }

    private static (int volume, bool isMuted) GetVolumeState()
    {
        var endpoint = GetEndpointVolume();
        if (endpoint is null)
        {
            return (-1, false);
        }

        endpoint.GetMasterVolumeLevelScalar(out var volume);
        endpoint.GetMute(out var isMuted);
        return (Math.Clamp((int)Math.Round(volume * 100.0f), 0, 100), isMuted);
    }

    private static IAudioEndpointVolume? GetEndpointVolume()
    {
        var enumerator = (IMMDeviceEnumerator)new MMDeviceEnumerator();
        enumerator.GetDefaultAudioEndpoint(EDataFlow.eRender, ERole.eMultimedia, out var device);
        if (device is null)
        {
            return null;
        }

        var iid = typeof(IAudioEndpointVolume).GUID;
        device.Activate(ref iid, CLSCTX.ALL, IntPtr.Zero, out var endpointObject);
        return endpointObject as IAudioEndpointVolume;
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

    [DllImport("user32.dll", SetLastError = true)]
    private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, IntPtr dwExtraInfo);

    [ComImport]
    [Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    private class MMDeviceEnumerator
    {
    }

    [ComImport]
    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMMDeviceEnumerator
    {
        int EnumAudioEndpoints(EDataFlow dataFlow, int dwStateMask, out IntPtr ppDevices);
        int GetDefaultAudioEndpoint(EDataFlow dataFlow, ERole role, out IMMDevice device);
    }

    [ComImport]
    [Guid("D666063F-1587-4E43-81F1-B948E807363F")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IMMDevice
    {
        int Activate(ref Guid iid, CLSCTX clsCtx, IntPtr activationParams, [MarshalAs(UnmanagedType.IUnknown)] out object interfacePtr);
    }

    [ComImport]
    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A")]
    [InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    private interface IAudioEndpointVolume
    {
        int RegisterControlChangeNotify(IntPtr notify);
        int UnregisterControlChangeNotify(IntPtr notify);
        int GetChannelCount(out uint channelCount);
        int SetMasterVolumeLevel(float level, Guid eventContext);
        int SetMasterVolumeLevelScalar(float level, Guid eventContext);
        int GetMasterVolumeLevel(out float level);
        int GetMasterVolumeLevelScalar(out float level);
        int SetMute([MarshalAs(UnmanagedType.Bool)] bool isMuted, Guid eventContext);
        int GetMute(out bool isMuted);
    }

    private enum EDataFlow
    {
        eRender,
        eCapture,
        eAll
    }

    private enum ERole
    {
        eConsole,
        eMultimedia,
        eCommunications
    }

    [Flags]
    private enum CLSCTX : uint
    {
        INPROC_SERVER = 0x1,
        INPROC_HANDLER = 0x2,
        LOCAL_SERVER = 0x4,
        ALL = INPROC_SERVER | INPROC_HANDLER | LOCAL_SERVER
    }
}
