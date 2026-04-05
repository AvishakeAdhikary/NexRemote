using System.Text.Json.Serialization;

namespace NexRemote.Models;

public sealed class FeatureStatusInfo
{
    [JsonPropertyName("supported")]
    public bool Supported { get; set; }

    [JsonPropertyName("available")]
    public bool Available { get; set; }

    [JsonPropertyName("reason")]
    public string Reason { get; set; } = string.Empty;

    [JsonPropertyName("action_required")]
    public string ActionRequired { get; set; } = string.Empty;
}
