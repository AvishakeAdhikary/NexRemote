using System;
using System.Collections.Concurrent;
using System.Threading;
using System.Threading.Tasks;

namespace NexRemote.Services;

public sealed class ConnectionApprovalService : IConnectionApprovalService
{
    private readonly ConcurrentDictionary<string, TaskCompletionSource<bool>> _pending = new(StringComparer.OrdinalIgnoreCase);

    public event EventHandler<PendingApprovalRequestEventArgs>? ApprovalRequested;

    public async Task<bool> RequestApprovalAsync(string deviceId, string deviceName, TimeSpan timeout, CancellationToken cancellationToken = default)
    {
        if (timeout <= TimeSpan.Zero)
        {
            timeout = TimeSpan.FromSeconds(60);
        }

        var newTcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var activeTcs = _pending.GetOrAdd(deviceId, newTcs);
        if (ReferenceEquals(activeTcs, newTcs))
        {
            ApprovalRequested?.Invoke(this, new PendingApprovalRequestEventArgs(deviceId, deviceName));
        }

        try
        {
            var completed = await activeTcs.Task.WaitAsync(timeout, cancellationToken).ConfigureAwait(false);
            return completed;
        }
        catch (TimeoutException)
        {
            return false;
        }
        finally
        {
            if (_pending.TryGetValue(deviceId, out var current) && ReferenceEquals(current, activeTcs))
            {
                _pending.TryRemove(deviceId, out _);
            }
        }
    }

    public void CompleteApproval(string deviceId, bool approved)
    {
        if (_pending.TryRemove(deviceId, out var tcs))
        {
            tcs.TrySetResult(approved);
        }
    }
}
