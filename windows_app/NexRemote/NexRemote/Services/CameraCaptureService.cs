using System;
using System.Collections.Generic;
using System.Linq;
using System.Collections.Concurrent;
using System.Threading.Tasks;
using Windows.Devices.Enumeration;

namespace NexRemote.Services;

internal sealed class CameraCaptureService
{
    private readonly ConcurrentDictionary<int, bool> _activeCameras = new();

    public async Task<IReadOnlyList<object>> GetCamerasAsync()
    {
        try
        {
            var devices = await DeviceInformation.FindAllAsync(DeviceClass.VideoCapture);
            return devices
                .Select((device, index) => (object)new
                {
                    index,
                    name = device.Name,
                    id = device.Id,
                    available = true
                })
                .ToList();
        }
        catch
        {
            return new List<object>();
        }
    }

    public object GetCameraInfo(int cameraIndex, string? cameraName = null)
    {
        return new
        {
            index = cameraIndex,
            name = cameraName ?? $"Camera {cameraIndex}",
            available = true,
            active = _activeCameras.ContainsKey(cameraIndex)
        };
    }

    public void StartCamera(int cameraIndex)
    {
        _activeCameras[cameraIndex] = true;
    }

    public void StopCamera(int cameraIndex)
    {
        _activeCameras.TryRemove(cameraIndex, out _);
    }

    public void StopAll()
    {
        _activeCameras.Clear();
    }
}
