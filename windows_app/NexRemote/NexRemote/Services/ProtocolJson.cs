using System.Text.Json;
using System.Text.Json.Serialization;

namespace NexRemote.Services;

public static class ProtocolJson
{
    private static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = null,
        PropertyNameCaseInsensitive = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = false
    };

    public static JsonSerializerOptions SharedOptions => Options;
}
