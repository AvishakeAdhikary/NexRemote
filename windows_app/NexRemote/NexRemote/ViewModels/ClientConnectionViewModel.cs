namespace NexRemote.ViewModels;

public sealed class ClientConnectionViewModel
{
    public required string ClientId { get; init; }
    public required string DisplayName { get; init; }
    public required string Summary { get; init; }
    public required string Status { get; init; }

    public override string ToString() => $"{DisplayName} | {Summary} | {Status}";
}
