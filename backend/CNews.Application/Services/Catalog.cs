namespace CNews.Application.Services;

public static class Catalog
{
    public static readonly IReadOnlyList<string> Topics =
    [
        "Top", "Canada", "Local", "World", "Politics", "Business", "Health", "Arts", "Technology", "Sports"
    ];

    public static readonly IReadOnlyList<string> DefaultTopics =
        ["Top", "Canada", "Local", "Business", "Health", "Politics"];

    public static IReadOnlyList<string> ParseTopics(string? raw, IReadOnlyList<string>? fallback = null)
    {
        fallback ??= DefaultTopics;
        if (string.IsNullOrWhiteSpace(raw))
        {
            return fallback;
        }

        var parts = raw.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var invalid = parts.Where(p => !Topics.Contains(p, StringComparer.OrdinalIgnoreCase)).ToArray();
        if (invalid.Length > 0)
        {
            throw new ArgumentException($"invalid_topic:{string.Join(',', invalid)}");
        }

        return parts
            .Select(p => Topics.First(t => t.Equals(p, StringComparison.OrdinalIgnoreCase)))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();
    }

    public static string Preview(string summary, int maxChars = 140)
    {
        var text = summary.Trim();
        if (text.Length <= maxChars)
        {
            return text;
        }

        return text[..(maxChars - 1)].TrimEnd() + "…";
    }
}
