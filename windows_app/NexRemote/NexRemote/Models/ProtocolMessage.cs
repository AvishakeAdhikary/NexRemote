using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class ProtocolMessage
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? ExtensionData { get; set; }
}
