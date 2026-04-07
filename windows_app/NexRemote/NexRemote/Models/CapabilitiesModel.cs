using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class CapabilitiesModel
{
    [JsonPropertyName("keyboard")]
    public bool Keyboard { get; set; } = true;

    [JsonPropertyName("mouse")]
    public bool Mouse { get; set; } = true;

    [JsonPropertyName("gamepad")]
    public bool Gamepad { get; set; } = true;

    [JsonPropertyName("gamepad_available")]
    public bool GamepadAvailable { get; set; }

    [JsonPropertyName("gamepad_mode")]
    public string GamepadMode { get; set; } = "xinput";

    [JsonPropertyName("gamepad_modes")]
    public List<string> GamepadModes { get; set; } = new() { "xinput", "dinput", "android" };

    [JsonPropertyName("screen_streaming")]
    public bool ScreenStreaming { get; set; } = true;

    [JsonPropertyName("screen_audio_streaming")]
    public bool ScreenAudioStreaming { get; set; } = true;

    [JsonPropertyName("camera_streaming")]
    public bool CameraStreaming { get; set; } = true;

    [JsonPropertyName("file_transfer")]
    public bool FileTransfer { get; set; } = true;

    [JsonPropertyName("clipboard")]
    public bool Clipboard { get; set; } = true;

    [JsonPropertyName("multi_display")]
    public bool MultiDisplay { get; set; } = true;

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? ExtensionData { get; set; }
}
