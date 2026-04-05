using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class DiscoveryResponse
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = "discovery_response";

    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;

    [JsonPropertyName("port")]
    public int Port { get; set; } = 8765;

    [JsonPropertyName("port_insecure")]
    public int PortInsecure { get; set; } = 8766;

    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;

    [JsonPropertyName("version")]
    public string Version { get; set; } = "1.0.0";

    [JsonExtensionData]
    public Dictionary<string, JsonElement>? ExtensionData { get; set; }
}
