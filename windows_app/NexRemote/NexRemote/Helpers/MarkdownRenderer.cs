using System;
using System.Text.RegularExpressions;
using Microsoft.UI;
using Microsoft.UI.Text;
using Microsoft.UI.Xaml.Documents;
using Microsoft.UI.Xaml.Media;
using Microsoft.UI.Xaml.Controls;

namespace NexRemote.Helpers;

internal static class MarkdownRenderer
{
    private static readonly Regex LinkPattern = new(@"\[(?<text>[^\]]+)\]\((?<url>[^)]+)\)", RegexOptions.Compiled);
    private static readonly Regex BoldPattern = new(@"\*\*(?<text>.+?)\*\*", RegexOptions.Compiled);
    private static readonly Regex ItalicPattern = new(@"\*(?<text>.+?)\*", RegexOptions.Compiled);

    public static RichTextBlock Build(string markdown)
    {
        var block = new RichTextBlock
        {
            IsTextSelectionEnabled = true,
            TextWrapping = Microsoft.UI.Xaml.TextWrapping.WrapWholeWords
        };

        foreach (var line in (markdown ?? string.Empty).Replace("\r\n", "\n").Split('\n'))
        {
            if (string.IsNullOrWhiteSpace(line))
            {
                block.Blocks.Add(new Paragraph());
                continue;
            }

            var paragraph = new Paragraph();
            if (line.StartsWith("### ", StringComparison.Ordinal))
            {
                paragraph.FontSize = 18;
                paragraph.FontWeight = FontWeights.SemiBold;
                AppendInlineMarkdown(paragraph, line[4..]);
            }
            else if (line.StartsWith("## ", StringComparison.Ordinal))
            {
                paragraph.FontSize = 22;
                paragraph.FontWeight = FontWeights.SemiBold;
                AppendInlineMarkdown(paragraph, line[3..]);
            }
            else if (line.StartsWith("# ", StringComparison.Ordinal))
            {
                paragraph.FontSize = 28;
                paragraph.FontWeight = FontWeights.Bold;
                AppendInlineMarkdown(paragraph, line[2..]);
            }
            else if (line.StartsWith("- ", StringComparison.Ordinal) || line.StartsWith("* ", StringComparison.Ordinal))
            {
                paragraph.TextIndent = -18;
                paragraph.Margin = new Microsoft.UI.Xaml.Thickness(18, 0, 0, 0);
                paragraph.Inlines.Add(new Run { Text = "\u2022 " });
                AppendInlineMarkdown(paragraph, line[2..]);
            }
            else
            {
                paragraph.FontSize = 14;
                AppendInlineMarkdown(paragraph, line);
            }

            block.Blocks.Add(paragraph);
        }

        return block;
    }

    private static void AppendInlineMarkdown(Paragraph paragraph, string text)
    {
        var remaining = text;
        while (!string.IsNullOrEmpty(remaining))
        {
            var linkMatch = LinkPattern.Match(remaining);
            if (!linkMatch.Success)
            {
                AppendStyledRuns(paragraph, remaining);
                break;
            }

            if (linkMatch.Index > 0)
            {
                AppendStyledRuns(paragraph, remaining[..linkMatch.Index]);
            }

            var hyperlink = new Hyperlink();
            hyperlink.Inlines.Add(new Run { Text = linkMatch.Groups["text"].Value });
            if (Uri.TryCreate(linkMatch.Groups["url"].Value, UriKind.Absolute, out var uri))
            {
                hyperlink.NavigateUri = uri;
            }
            paragraph.Inlines.Add(hyperlink);
            remaining = remaining[(linkMatch.Index + linkMatch.Length)..];
        }
    }

    private static void AppendStyledRuns(Paragraph paragraph, string text)
    {
        var cursor = 0;
        while (cursor < text.Length)
        {
            var boldMatch = BoldPattern.Match(text, cursor);
            var italicMatch = ItalicPattern.Match(text, cursor);
            var next = SelectNextMatch(boldMatch, italicMatch);
            if (next is null || !next.Success)
            {
                paragraph.Inlines.Add(new Run { Text = text[cursor..] });
                return;
            }

            if (next.Index > cursor)
            {
                paragraph.Inlines.Add(new Run { Text = text[cursor..next.Index] });
            }

            if (ReferenceEquals(next, boldMatch))
            {
                var bold = new Bold();
                bold.Inlines.Add(new Run { Text = boldMatch.Groups["text"].Value });
                paragraph.Inlines.Add(bold);
            }
            else
            {
                var italic = new Italic();
                italic.Inlines.Add(new Run { Text = italicMatch.Groups["text"].Value });
                paragraph.Inlines.Add(italic);
            }

            cursor = next.Index + next.Length;
        }
    }

    private static Match? SelectNextMatch(Match boldMatch, Match italicMatch)
    {
        if (boldMatch.Success && italicMatch.Success)
        {
            return boldMatch.Index <= italicMatch.Index ? boldMatch : italicMatch;
        }

        if (boldMatch.Success)
        {
            return boldMatch;
        }

        if (italicMatch.Success)
        {
            return italicMatch;
        }

        return null;
    }
}
