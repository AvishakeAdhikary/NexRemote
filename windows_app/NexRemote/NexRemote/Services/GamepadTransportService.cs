using System;
using System.Collections.Concurrent;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using Nefarius.ViGEm.Client;
using Nefarius.ViGEm.Client.Targets;
using Nefarius.ViGEm.Client.Targets.Xbox360;

namespace NexRemote.Services;

public interface IGamepadTransportService : IDisposable
{
    bool IsReady { get; }
    bool TryHandleInput(string clientId, JsonElement message);
    void DisconnectClient(string clientId);
}

public sealed class GamepadTransportService : IGamepadTransportService
{
    private static readonly TimeSpan RetryInterval = TimeSpan.FromSeconds(5);
    private readonly ILogger<GamepadTransportService> _logger;
    private readonly object _gate = new();
    private readonly ConcurrentDictionary<string, ControllerSession> _sessions = new(StringComparer.OrdinalIgnoreCase);
    private ViGEmClient? _client;
    private DateTimeOffset _lastInitAttempt = DateTimeOffset.MinValue;

    public GamepadTransportService(ILogger<GamepadTransportService> logger)
    {
        _logger = logger;
    }

    public bool IsReady => EnsureClient() is not null;

    public bool TryHandleInput(string clientId, JsonElement message)
    {
        var client = EnsureClient();
        if (client is null || string.IsNullOrWhiteSpace(clientId))
        {
            return false;
        }

        try
        {
            var session = _sessions.GetOrAdd(clientId, _ => CreateSession(client));
            ApplyInput(session, message);
            session.Controller.SubmitReport();
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to apply gamepad input for client {ClientId}", clientId);
            return false;
        }
    }

    public void DisconnectClient(string clientId)
    {
        if (!_sessions.TryRemove(clientId, out var session))
        {
            return;
        }

        try
        {
            ResetController(session);
            session.Controller.Disconnect();
        }
        catch (Exception ex)
        {
            _logger.LogDebug(ex, "Failed to disconnect virtual controller for client {ClientId}", clientId);
        }
    }

    public void Dispose()
    {
        foreach (var clientId in _sessions.Keys)
        {
            DisconnectClient(clientId);
        }

        _client?.Dispose();
        _client = null;
    }

    private ViGEmClient? EnsureClient()
    {
        lock (_gate)
        {
            if (_client is not null)
            {
                return _client;
            }

            if (DateTimeOffset.UtcNow - _lastInitAttempt < RetryInterval)
            {
                return null;
            }

            _lastInitAttempt = DateTimeOffset.UtcNow;

            try
            {
                _client = new ViGEmClient();
                return _client;
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Unable to initialize ViGEm client.");
                return null;
            }
        }
    }

    private ControllerSession CreateSession(ViGEmClient client)
    {
        var controller = client.CreateXbox360Controller();
        controller.Connect();
        return new ControllerSession(controller);
    }

    private static void ApplyInput(ControllerSession session, JsonElement message)
    {
        var inputType = ReadString(message, "input_type");
        switch (inputType.ToLowerInvariant())
        {
            case "button":
                ApplyButton(session.Controller, ReadString(message, "button"), ReadBoolean(message, "pressed"));
                break;
            case "dpad":
                ApplyDpad(session.Controller, ReadString(message, "direction"), ReadBoolean(message, "pressed"));
                break;
            case "joystick":
                ApplyJoystick(session.Controller, ReadString(message, "stick"), ReadSingle(message, "x"), ReadSingle(message, "y"));
                break;
            case "trigger":
                ApplyTrigger(session.Controller, ReadString(message, "trigger"), ReadSingle(message, "value"));
                break;
            case "gyro":
                ApplyGyro(session.Controller, session, ReadSingle(message, "x"), ReadSingle(message, "y"));
                break;
        }
    }

    private static void ApplyButton(IXbox360Controller controller, string buttonName, bool pressed)
    {
        if (TryMapButton(buttonName, out var button))
        {
            controller.SetButtonState(button, pressed);
        }
    }

    private static void ApplyDpad(IXbox360Controller controller, string direction, bool pressed)
    {
        switch (direction.ToUpperInvariant())
        {
            case "UP":
                controller.SetButtonState(Xbox360Button.Up, pressed);
                break;
            case "DOWN":
                controller.SetButtonState(Xbox360Button.Down, pressed);
                break;
            case "LEFT":
                controller.SetButtonState(Xbox360Button.Left, pressed);
                break;
            case "RIGHT":
                controller.SetButtonState(Xbox360Button.Right, pressed);
                break;
        }
    }

    private static void ApplyJoystick(IXbox360Controller controller, string stick, float x, float y)
    {
        var xValue = ToAxisValue(x);
        var yValue = ToAxisValue(y);

        if (string.Equals(stick, "right", StringComparison.OrdinalIgnoreCase))
        {
            controller.SetAxisValue(Xbox360Axis.RightThumbX, xValue);
            controller.SetAxisValue(Xbox360Axis.RightThumbY, yValue);
            return;
        }

        controller.SetAxisValue(Xbox360Axis.LeftThumbX, xValue);
        controller.SetAxisValue(Xbox360Axis.LeftThumbY, yValue);
    }

    private static void ApplyTrigger(IXbox360Controller controller, string trigger, float value)
    {
        var sliderValue = ToTriggerValue(value);
        if (string.Equals(trigger, "RT", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(trigger, "R2", StringComparison.OrdinalIgnoreCase))
        {
            controller.SetSliderValue(Xbox360Slider.RightTrigger, sliderValue);
            return;
        }

        controller.SetSliderValue(Xbox360Slider.LeftTrigger, sliderValue);
    }

    private static void ApplyGyro(IXbox360Controller controller, ControllerSession session, float x, float y)
    {
        session.RightStickX = Math.Clamp(session.RightStickX + x * 0.06f, -1f, 1f);
        session.RightStickY = Math.Clamp(session.RightStickY - y * 0.06f, -1f, 1f);
        controller.SetAxisValue(Xbox360Axis.RightThumbX, ToAxisValue(session.RightStickX));
        controller.SetAxisValue(Xbox360Axis.RightThumbY, ToAxisValue(session.RightStickY));
    }

    private static void ResetController(ControllerSession session)
    {
        foreach (Xbox360Button button in Enum.GetValues(typeof(Xbox360Button)))
        {
            session.Controller.SetButtonState(button, false);
        }

        session.Controller.SetAxisValue(Xbox360Axis.LeftThumbX, 0);
        session.Controller.SetAxisValue(Xbox360Axis.LeftThumbY, 0);
        session.Controller.SetAxisValue(Xbox360Axis.RightThumbX, 0);
        session.Controller.SetAxisValue(Xbox360Axis.RightThumbY, 0);
        session.Controller.SetSliderValue(Xbox360Slider.LeftTrigger, 0);
        session.Controller.SetSliderValue(Xbox360Slider.RightTrigger, 0);
        session.Controller.SubmitReport();
    }

    private static bool TryMapButton(string buttonName, out Xbox360Button button)
    {
        switch (buttonName.ToUpperInvariant())
        {
            case "A":
                button = Xbox360Button.A;
                return true;
            case "B":
                button = Xbox360Button.B;
                return true;
            case "X":
                button = Xbox360Button.X;
                return true;
            case "Y":
                button = Xbox360Button.Y;
                return true;
            case "L1":
            case "LB":
                button = Xbox360Button.LeftShoulder;
                return true;
            case "R1":
            case "RB":
                button = Xbox360Button.RightShoulder;
                return true;
            case "SELECT":
            case "BACK":
                button = Xbox360Button.Back;
                return true;
            case "START":
                button = Xbox360Button.Start;
                return true;
            case "GUIDE":
            case "HOME":
                button = Xbox360Button.Guide;
                return true;
            case "L3":
                button = Xbox360Button.LeftThumb;
                return true;
            case "R3":
                button = Xbox360Button.RightThumb;
                return true;
            default:
                button = Xbox360Button.A;
                return false;
        }
    }

    private static short ToAxisValue(float value)
        => (short)Math.Round(Math.Clamp(value, -1f, 1f) * short.MaxValue);

    private static byte ToTriggerValue(float value)
        => (byte)Math.Round(Math.Clamp(value, 0f, 1f) * byte.MaxValue);

    private static string ReadString(JsonElement element, string propertyName)
        => element.TryGetProperty(propertyName, out var property) && property.ValueKind == JsonValueKind.String
            ? property.GetString() ?? string.Empty
            : string.Empty;

    private static bool ReadBoolean(JsonElement element, string propertyName)
        => element.TryGetProperty(propertyName, out var property) && property.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? property.GetBoolean()
            : false;

    private static float ReadSingle(JsonElement element, string propertyName)
    {
        if (element.TryGetProperty(propertyName, out var property) && property.TryGetSingle(out var value))
        {
            return value;
        }

        return 0f;
    }

    private sealed class ControllerSession
    {
        public ControllerSession(IXbox360Controller controller)
        {
            Controller = controller;
        }

        public IXbox360Controller Controller { get; }
        public float RightStickX { get; set; }
        public float RightStickY { get; set; }
    }
}
