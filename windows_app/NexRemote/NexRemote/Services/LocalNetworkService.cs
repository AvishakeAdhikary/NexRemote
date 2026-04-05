using System.Net;
using System.Net.Sockets;

namespace NexRemote.Services;

public interface ILocalNetworkService
{
    string GetLanIpAddress();
}

public sealed class LocalNetworkService : ILocalNetworkService
{
    public string GetLanIpAddress()
    {
        try
        {
            using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
            socket.Connect("8.8.8.8", 80);
            if (socket.LocalEndPoint is IPEndPoint endpoint)
            {
                return endpoint.Address.ToString();
            }
        }
        catch
        {
            // fall back below
        }

        return IPAddress.Loopback.ToString();
    }
}
