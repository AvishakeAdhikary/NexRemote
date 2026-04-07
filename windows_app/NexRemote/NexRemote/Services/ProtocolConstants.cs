namespace NexRemote.Services;

public static class ProtocolConstants
{
    public const string Version = "1.0.0";
    public const string DiscoveryMagic = "NEXREMOTE_DISCOVER";
    public const int DefaultSecurePort = 8765;
    public const int DefaultInsecurePort = 8766;
    public const int DefaultDiscoveryPort = 37020;
    public const int ApprovalTimeoutSeconds = 12;
    public const string ScreenFrameHeader = "SCRN";
    public const string CameraFrameHeader = "CAMF";
    public const string ScreenAudioFrameHeader = "AUDF";
    public const string AuthType = "auth";
    public const string DiscoveryResponseType = "discovery_response";
    public const string AuthSuccessType = "auth_success";
    public const string AuthFailedType = "auth_failed";
    public const string AuthChallengeType = "auth_challenge";
    public const string AuthResponseType = "auth_response";
    public const string ConnectionRejectedType = "connection_rejected";
    public const string PingType = "ping";
    public const string PongType = "pong";
}
