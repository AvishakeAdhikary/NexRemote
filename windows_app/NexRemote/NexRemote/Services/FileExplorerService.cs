using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;

namespace NexRemote.Services;

internal sealed class FileExplorerService
{
    private readonly string[] _allowedRoots =
    [
        Path.GetPathRoot(Environment.SystemDirectory) ?? @"C:\",
        Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)
    ];

    private readonly long _maxReadSize = 5L * 1024 * 1024;

    public Task<object> HandleRequestAsync(JsonElement data)
    {
        try
        {
            var action = GetString(data, "action");
            object response = action switch
            {
                "list" => ListDirectory(GetString(data, "path", @"C:\")),
                "open" => OpenPath(GetString(data, "path")),
                "properties" => GetProperties(GetString(data, "path")),
                "search" => Search(GetString(data, "path", @"C:\"), GetString(data, "query")),
                "copy_path" => new { type = "file_explorer", action = "path_copied", path = GetString(data, "path") },
                "create_folder" => CreateFolder(GetString(data, "path"), GetString(data, "name")),
                "create_file" => CreateFile(GetString(data, "path"), GetString(data, "name"), GetString(data, "content")),
                "rename" => Rename(GetString(data, "path"), GetString(data, "new_name")),
                "delete" => Delete(GetString(data, "path")),
                "read_file" => ReadFile(GetString(data, "path")),
                "write_file" => WriteFile(GetString(data, "path"), GetString(data, "content")),
                "copy" => Copy(GetString(data, "source"), GetString(data, "destination")),
                "move" => Move(GetString(data, "source"), GetString(data, "destination")),
                _ => new { type = "file_explorer", action = "error", message = $"Unknown action: {action}" }
            };

            return Task.FromResult(response);
        }
        catch (Exception ex)
        {
            return Task.FromResult<object>(new { type = "file_explorer", action = "error", message = ex.Message });
        }
    }

    private object ListDirectory(string path)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var items = new List<FileItem>();
            foreach (var entry in Directory.EnumerateFileSystemEntries(path))
            {
                try
                {
                    var fileInfo = new FileInfo(entry);
                    var directoryInfo = new DirectoryInfo(entry);
                    var isDirectory = directoryInfo.Exists;
                    var stat = (FileSystemInfo)(isDirectory ? directoryInfo : fileInfo);

                    items.Add(new FileItem
                    {
                        Name = Path.GetFileName(entry),
                        FilePath = entry,
                        IsDirectory = isDirectory,
                        Size = isDirectory ? null : fileInfo.Length,
                        Modified = stat.LastWriteTime.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture)
                    });
                }
                catch
                {
                    // Skip inaccessible entries.
                }
            }

            var ordered = items
                .OrderBy(item => !item.IsDirectory)
                .ThenBy(item => item.Name.ToLowerInvariant())
                .ToList();

            return new
            {
                type = "file_explorer",
                action = "list",
                path,
                files = ordered
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to list directory: {ex.Message}");
        }
    }

    private object OpenPath(string path)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            if (File.Exists(path))
            {
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
                return new { type = "file_explorer", action = "file_opened", path };
            }

            if (Directory.Exists(path))
            {
                Process.Start(new ProcessStartInfo("explorer.exe", $"\"{path}\"") { UseShellExecute = true });
                return new { type = "file_explorer", action = "folder_opened", path };
            }

            return Error("File or folder not found");
        }
        catch (Exception ex)
        {
            return Error($"Failed to open: {ex.Message}");
        }
    }

    private object GetProperties(string path)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var fileInfo = new FileInfo(path);
            var directoryInfo = new DirectoryInfo(path);
            var isDirectory = directoryInfo.Exists;
            if (!isDirectory && !fileInfo.Exists)
            {
                return Error("File or folder not found");
            }

            var stat = (FileSystemInfo)(isDirectory ? directoryInfo : fileInfo);

            return new
            {
                type = "file_explorer",
                action = "properties",
                path,
                name = Path.GetFileName(path),
                is_directory = isDirectory,
                size = isDirectory ? 0L : fileInfo.Length,
                created = stat.CreationTime.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                modified = stat.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                accessed = stat.LastAccessTime.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture)
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to get properties: {ex.Message}");
        }
    }

    private object Search(string path, string query)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var items = new List<object>();
            var needle = query.ToLowerInvariant();

            foreach (var entry in Directory.EnumerateFileSystemEntries(path))
            {
                try
                {
                    var name = Path.GetFileName(entry);
                    if (!name.ToLowerInvariant().Contains(needle))
                    {
                        continue;
                    }

                    var fileInfo = new FileInfo(entry);
                    var directoryInfo = new DirectoryInfo(entry);
                    var isDirectory = directoryInfo.Exists;
                    var stat = (FileSystemInfo)(isDirectory ? directoryInfo : fileInfo);

                    items.Add(new
                    {
                        name,
                        path = entry,
                        is_directory = isDirectory,
                        size = isDirectory ? (long?)null : fileInfo.Length,
                        modified = stat.LastWriteTime.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture)
                    });
                }
                catch
                {
                    // Skip inaccessible entries.
                }
            }

            var ordered = items
                .Cast<dynamic>()
                .OrderBy(item => !(bool)item.is_directory)
                .ThenBy(item => ((string)item.name).ToLowerInvariant())
                .Cast<object>()
                .ToList();

            return new
            {
                type = "file_explorer",
                action = "search",
                path,
                query,
                files = ordered
            };
        }
        catch (Exception ex)
        {
            return Error($"Search failed: {ex.Message}");
        }
    }

    private object CreateFolder(string parentPath, string name)
    {
        if (!ValidatePath(parentPath))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var newPath = Path.Combine(parentPath, name);
            if (Directory.Exists(newPath) || File.Exists(newPath))
            {
                return Error($"Folder \"{name}\" already exists");
            }

            Directory.CreateDirectory(newPath);
            return new
            {
                type = "file_explorer",
                action = "folder_created",
                path = newPath,
                name
            };
        }
        catch (IOException)
        {
            return Error($"Folder \"{name}\" already exists");
        }
        catch (Exception ex)
        {
            return Error($"Failed to create folder: {ex.Message}");
        }
    }

    private object CreateFile(string parentPath, string name, string content)
    {
        if (!ValidatePath(parentPath))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var newPath = Path.Combine(parentPath, name);
            if (File.Exists(newPath))
            {
                return Error($"File \"{name}\" already exists");
            }

            File.WriteAllText(newPath, content ?? string.Empty);
            return new
            {
                type = "file_explorer",
                action = "file_created",
                path = newPath,
                name
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to create file: {ex.Message}");
        }
    }

    private object Rename(string path, string newName)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var parent = Path.GetDirectoryName(path) ?? string.Empty;
            var newPath = Path.Combine(parent, newName);
            if (File.Exists(newPath) || Directory.Exists(newPath))
            {
                return Error($"\"{newName}\" already exists");
            }

            if (Directory.Exists(path))
            {
                Directory.Move(path, newPath);
            }
            else
            {
                File.Move(path, newPath);
            }

            return new
            {
                type = "file_explorer",
                action = "renamed",
                old_path = path,
                new_path = newPath,
                new_name = newName
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to rename: {ex.Message}");
        }
    }

    private object Delete(string path)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var name = Path.GetFileName(path);
            if (Directory.Exists(path))
            {
                Directory.Delete(path, recursive: true);
            }
            else if (File.Exists(path))
            {
                File.Delete(path);
            }
            else
            {
                return Error("File or folder not found");
            }

            return new
            {
                type = "file_explorer",
                action = "deleted",
                path,
                name
            };
        }
        catch (UnauthorizedAccessException)
        {
            return Error($"Permission denied: cannot delete \"{Path.GetFileName(path)}\"");
        }
        catch (Exception ex)
        {
            return Error($"Failed to delete: {ex.Message}");
        }
    }

    private object ReadFile(string path)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            if (!File.Exists(path))
            {
                return Error("Not a file");
            }

            var fileInfo = new FileInfo(path);
            if (fileInfo.Length > _maxReadSize)
            {
                return Error($"File too large ({fileInfo.Length} bytes). Max: {_maxReadSize} bytes");
            }

            var content = File.ReadAllText(path);
            return new
            {
                type = "file_explorer",
                action = "file_content",
                path,
                name = Path.GetFileName(path),
                content
            };
        }
        catch (UnauthorizedAccessException)
        {
            return Error("Cannot read binary file as text");
        }
        catch (Exception ex)
        {
            return Error($"Failed to read file: {ex.Message}");
        }
    }

    private object WriteFile(string path, string content)
    {
        if (!ValidatePath(path))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            File.WriteAllText(path, content ?? string.Empty);
            return new
            {
                type = "file_explorer",
                action = "file_saved",
                path,
                name = Path.GetFileName(path),
                size = (content ?? string.Empty).Length
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to write file: {ex.Message}");
        }
    }

    private object Copy(string source, string destination)
    {
        if (!ValidatePath(source) || !ValidatePath(destination))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var destinationPath = Path.Combine(destination, Path.GetFileName(source));
            if (Directory.Exists(source))
            {
                CopyDirectory(source, destinationPath);
            }
            else
            {
                File.Copy(source, destinationPath, overwrite: false);
            }

            return new
            {
                type = "file_explorer",
                action = "copied",
                source,
                destination = destinationPath
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to copy: {ex.Message}");
        }
    }

    private object Move(string source, string destination)
    {
        if (!ValidatePath(source) || !ValidatePath(destination))
        {
            return Error("Invalid or restricted path");
        }

        try
        {
            var destinationPath = Path.Combine(destination, Path.GetFileName(source));
            if (Directory.Exists(source))
            {
                Directory.Move(source, destinationPath);
            }
            else
            {
                File.Move(source, destinationPath, overwrite: false);
            }

            return new
            {
                type = "file_explorer",
                action = "moved",
                source,
                destination = destinationPath
            };
        }
        catch (Exception ex)
        {
            return Error($"Failed to move: {ex.Message}");
        }
    }

    private bool ValidatePath(string path)
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            return false;
        }

        try
        {
            var resolved = Path.GetFullPath(path);
            return _allowedRoots.Any(root => !string.IsNullOrWhiteSpace(root) &&
                                             resolved.StartsWith(Path.GetFullPath(root), StringComparison.OrdinalIgnoreCase));
        }
        catch
        {
            return false;
        }
    }

    private static object Error(string message)
        => new { type = "file_explorer", action = "error", message };

    private static string GetString(JsonElement element, string propertyName, string fallback = "")
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var prop) &&
            prop.ValueKind == JsonValueKind.String)
        {
            return prop.GetString() ?? fallback;
        }

        return fallback;
    }

    private static void CopyDirectory(string source, string destination)
    {
        Directory.CreateDirectory(destination);
        foreach (var directory in Directory.GetDirectories(source))
        {
            CopyDirectory(directory, Path.Combine(destination, Path.GetFileName(directory)));
        }

        foreach (var file in Directory.GetFiles(source))
        {
            File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), overwrite: false);
        }
    }

    private sealed class FileItem
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("path")]
        public string FilePath { get; set; } = string.Empty;

        [JsonPropertyName("is_directory")]
        public bool IsDirectory { get; set; }

        [JsonPropertyName("size")]
        public long? Size { get; set; }

        [JsonPropertyName("modified")]
        public string Modified { get; set; } = string.Empty;
    }
}
