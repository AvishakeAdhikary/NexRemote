using System;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using Microsoft.Windows.AppLifecycle;
using NexRemote.Bootstrap;

namespace NexRemote;

public partial class App : Application
{
    private Window? _window;
    private AppInstance? _mainInstance;

    public App()
    {
        InitializeComponent();
    }

    public static IHost Host { get; private set; } = null!;

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        if (!await EnsureSingleInstanceAsync())
        {
            return;
        }

        Host = AppBootstrapper.Build();
        await AppBootstrapper.InitializeAsync(Host.Services);

        _window = new MainWindow(Host.Services);
        _window.Activate();
    }

    private async Task<bool> EnsureSingleInstanceAsync()
    {
        var current = AppInstance.GetCurrent();
        var keyInstance = AppInstance.FindOrRegisterForKey("main");
        if (!keyInstance.IsCurrent)
        {
            await keyInstance.RedirectActivationToAsync(current.GetActivatedEventArgs());
            Exit();
            return false;
        }

        _mainInstance = keyInstance;
        _mainInstance.Activated += OnAppActivated;
        return true;
    }

    private void OnAppActivated(object? sender, AppActivationArguments args)
    {
        if (_window is null)
        {
            return;
        }

        DispatcherQueue.GetForCurrentThread().TryEnqueue(() =>
        {
            if (_window is MainWindow mainWindow)
            {
                mainWindow.RestoreFromActivation();
            }

            _window.Activate();
        });
    }
}
