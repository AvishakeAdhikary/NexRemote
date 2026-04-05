using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class TrustedDeviceRecord
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("first_connected")]
    public DateTimeOffset FirstConnected { get; set; } = DateTimeOffset.UtcNow;

    [JsonPropertyName("last_connected")]
    public DateTimeOffset LastConnected { get; set; } = DateTimeOffset.UtcNow;

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? ExtensionData { get; set; }
}
