using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using NexRemote.Helpers;
using NexRemote.Models;
using NexRemote.Services;

namespace NexRemote;

public sealed class LegalDocumentWindow : Window
{
    public LegalDocumentWindow(string title, string body, IThemeService themeService, ThemePreference themePreference)
    {
        Title = title;

        var root = new Grid
        {
            Background = (Brush)Application.Current.Resources["ApplicationPageBackgroundThemeBrush"]
        };

        root.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        root.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });

        var header = new StackPanel
        {
            Spacing = 8,
            Margin = new Thickness(24, 24, 24, 16)
        };
        header.Children.Add(new TextBlock
        {
            Text = title,
            FontSize = 28,
            FontWeight = Microsoft.UI.Text.FontWeights.SemiBold
        });
        header.Children.Add(new TextBlock
        {
            Text = "Review this document in full before accepting it for first-time access.",
            Opacity = 0.72,
            TextWrapping = TextWrapping.WrapWholeWords
        });
        root.Children.Add(header);

        var viewer = new ScrollViewer
        {
            Margin = new Thickness(24, 0, 24, 24),
            Content = MarkdownRenderer.Build(body)
        };
        Grid.SetRow(viewer, 1);
        root.Children.Add(viewer);

        Content = root;
        themeService.ApplyTheme(this, themePreference);
    }
}
