namespace NexRemote.Services;

public sealed class ServerState
{
    public bool Running { get; set; }
    public string? LastHost { get; set; }
    public int ConnectedClients { get; set; }
}
