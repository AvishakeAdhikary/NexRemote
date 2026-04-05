using Microsoft.UI.Xaml;
using NexRemote.Models;

namespace NexRemote.Services;

public interface IThemeService
{
    void ApplyTheme(Window window, ThemePreference preference);
}

public sealed class ThemeService : IThemeService
{
    public void ApplyTheme(Window window, ThemePreference preference)
    {
        if (window.Content is not FrameworkElement root)
        {
            return;
        }

        root.RequestedTheme = preference switch
        {
            ThemePreference.Light => ElementTheme.Light,
            ThemePreference.Dark => ElementTheme.Dark,
            _ => ElementTheme.Default
        };
    }
}
