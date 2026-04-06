using System;
using System.Threading.Tasks;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Xaml;
using Microsoft.Windows.AppLifecycle;
using NexRemote.Bootstrap;
using NexRemote.Services;
using Serilog;

namespace NexRemote;

public partial class App : Application
{
    private Window? _window;
    private AppInstance? _mainInstance;
    private static int _shutdownStarted;

    public App()
    {
        LoggingBootstrapper.ConfigureBootstrapLogger();
        RegisterGlobalExceptionHandlers();
        UnhandledException += OnUnhandledException;
        InitializeComponent();
    }

    public static IHost Host { get; private set; } = null!;

    protected override async void OnLaunched(LaunchActivatedEventArgs args)
    {
        if (!await EnsureSingleInstanceAsync())
        {
            return;
        }

        try
        {
            Host = AppBootstrapper.Build();
            await AppBootstrapper.InitializeAsync(Host.Services);
            await Host.StartAsync();

            _window = new MainWindow(Host.Services);
            _window.Activate();
        }
        catch (Exception ex)
        {
            Log.Fatal(ex, "Application launch failed");
            await ShutdownAsync().ConfigureAwait(false);
            throw;
        }
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

    public static async Task ShutdownAsync()
    {
        if (System.Threading.Interlocked.Exchange(ref _shutdownStarted, 1) == 1)
        {
            return;
        }

        try
        {
            if (Host is not null)
            {
                var coordinator = Host.Services.GetService<IServerCoordinator>();
                if (coordinator is not null)
                {
                    await coordinator.StopAsync().ConfigureAwait(false);
                }

                await Host.StopAsync().ConfigureAwait(false);
                Host.Dispose();
            }
        }
        catch (Exception ex)
        {
            Log.Error(ex, "Shutdown encountered an error");
        }
        finally
        {
            Log.CloseAndFlush();
        }
    }

    private void OnAppActivated(object? sender, AppActivationArguments args)
    {
        if (_window is null)
        {
            return;
        }

        _window.DispatcherQueue.TryEnqueue(() =>
        {
            if (_window is MainWindow mainWindow)
            {
                mainWindow.RestoreFromActivation();
            }

            _window.Activate();
        });
    }

    private static void RegisterGlobalExceptionHandlers()
    {
        AppDomain.CurrentDomain.UnhandledException += (_, args) =>
        {
            if (args.ExceptionObject is Exception ex)
            {
                Log.Fatal(ex, "Unhandled AppDomain exception");
            }
            else
            {
                Log.Fatal("Unhandled AppDomain exception: {ExceptionObject}", args.ExceptionObject);
            }
        };

        TaskScheduler.UnobservedTaskException += (_, args) =>
        {
            Log.Fatal(args.Exception, "Unobserved task exception");
            args.SetObserved();
        };
    }

    private void OnUnhandledException(object sender, Microsoft.UI.Xaml.UnhandledExceptionEventArgs e)
    {
        Log.Fatal(e.Exception, "Unhandled UI exception");
        e.Handled = true;
        _ = ShutdownAsync();
    }
}
