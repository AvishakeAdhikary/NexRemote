namespace NexRemote.ViewModels;

public sealed class TrustedDeviceViewModel
{
    public required string DeviceId { get; init; }
    public required string Name { get; init; }
    public required string Summary { get; init; }

    public override string ToString() => $"{Name} | {Summary}";
}
