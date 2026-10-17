namespace CNews.Application.Services;

public static class SearchQuery
{
    public const int MinLength = 2;
    public const int MaxLength = 80;

    public static string? Normalize(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return null;
        }

        var q = raw.Trim();
        if (q.Length < MinLength)
        {
            return null;
        }

        return q.Length > MaxLength ? q[..MaxLength] : q;
    }
}
