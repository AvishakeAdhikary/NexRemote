using NexRemote.Models;

namespace NexRemote.Services;

public interface IServerCapabilitiesFactory
{
    CapabilitiesModel Create(bool gamepadAvailable, string gamepadMode);
}

public sealed class ServerCapabilitiesFactory : IServerCapabilitiesFactory
{
    public CapabilitiesModel Create(bool gamepadAvailable, string gamepadMode)
    {
        return new CapabilitiesModel
        {
            Gamepad = gamepadAvailable,
            GamepadAvailable = gamepadAvailable,
            GamepadMode = string.IsNullOrWhiteSpace(gamepadMode) ? "xinput" : gamepadMode
        };
    }
}
