using System;
using System.Threading.Tasks;
using Windows.Devices.Enumeration;
using Windows.System;

namespace NexRemote.Services;

public enum CameraAccessState
{
    Unknown,
    Allowed,
    DeniedBySystem,
    DeniedByUser,
    Unspecified
}

public interface ICameraPermissionService
{
    Task<CameraAccessState> GetAccessStateAsync();
    Task OpenPrivacySettingsAsync();
}

public sealed class CameraPermissionService : ICameraPermissionService
{
    public Task<CameraAccessState> GetAccessStateAsync()
    {
        try
        {
            var status = DeviceAccessInformation.CreateFromDeviceClass(DeviceClass.VideoCapture).CurrentStatus;
            return Task.FromResult(status switch
            {
                DeviceAccessStatus.Allowed => CameraAccessState.Allowed,
                DeviceAccessStatus.DeniedBySystem => CameraAccessState.DeniedBySystem,
                DeviceAccessStatus.DeniedByUser => CameraAccessState.DeniedByUser,
                DeviceAccessStatus.Unspecified => CameraAccessState.Unspecified,
                _ => CameraAccessState.Unknown
            });
        }
        catch
        {
            return Task.FromResult(CameraAccessState.Unknown);
        }
    }

    public async Task OpenPrivacySettingsAsync()
    {
        await Launcher.LaunchUriAsync(new Uri("ms-settings:privacy-webcam"));
    }
}
