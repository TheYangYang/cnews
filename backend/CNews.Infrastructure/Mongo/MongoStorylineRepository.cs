using System.Text;
using System.Text.Json;
using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using MongoDB.Bson;
using MongoDB.Driver;

namespace CNews.Infrastructure.Mongo;

public sealed class MongoStorylineRepository(IOptions<MongoOptions> options) : IStorylineRepository
{
    private readonly IMongoCollection<BsonDocument> _threads =
        new MongoClient(options.Value.Uri).GetDatabase(options.Value.Database).GetCollection<BsonDocument>("threads");

    public async Task<(IReadOnlyList<Storyline> Items, string? NextCursor)> ListAsync(
        string status,
        IReadOnlyList<string>? topics,
        int limit,
        string? cursor,
        CancellationToken ct)
    {
        var filters = new List<FilterDefinition<BsonDocument>>();
        if (!string.Equals(status, "all", StringComparison.OrdinalIgnoreCase))
        {
            var mapped = string.Equals(status, "closed", StringComparison.OrdinalIgnoreCase) ? "closed" : "open";
            filters.Add(Builders<BsonDocument>.Filter.Eq("status", mapped));
        }

        if (topics is { Count: > 0 })
        {
            filters.Add(Builders<BsonDocument>.Filter.In("topic", topics));
        }

        if (!string.IsNullOrWhiteSpace(cursor) && TryDecodeCursor(cursor, out var cursorTime, out var cursorId))
        {
            filters.Add(Builders<BsonDocument>.Filter.Or(
                Builders<BsonDocument>.Filter.Lt("updatedAt", cursorTime),
                Builders<BsonDocument>.Filter.And(
                    Builders<BsonDocument>.Filter.Eq("updatedAt", cursorTime),
                    Builders<BsonDocument>.Filter.Lt("threadId", cursorId))));
        }

        var filter = filters.Count == 0
            ? Builders<BsonDocument>.Filter.Empty
            : Builders<BsonDocument>.Filter.And(filters);

        var docs = await _threads.Find(filter)
            .Sort(Builders<BsonDocument>.Sort.Descending("updatedAt").Descending("threadId"))
            .Limit(limit)
            .ToListAsync(ct);

        var items = docs.Select(Map).ToArray();
        string? next = null;
        if (items.Length == limit)
        {
            var last = items[^1];
            next = EncodeCursor(last.UpdatedAt.UtcDateTime, last.ThreadId);
        }

        return (items, next);
    }

    public async Task<Storyline?> GetByIdAsync(string threadId, CancellationToken ct)
    {
        var filter = Builders<BsonDocument>.Filter.Or(
            Builders<BsonDocument>.Filter.Eq("threadId", threadId),
            Builders<BsonDocument>.Filter.Eq("threadId", threadId.StartsWith("thread_") ? threadId : $"thread_{threadId}"));
        var doc = await _threads.Find(filter).FirstOrDefaultAsync(ct);
        return doc is null ? null : Map(doc);
    }

    private static Storyline Map(BsonDocument doc)
    {
        var updates = new List<StorylineUpdate>();
        if (doc.Contains("updates") && doc["updates"].IsBsonArray)
        {
            foreach (var item in doc["updates"].AsBsonArray)
            {
                var u = item.AsBsonDocument;
                updates.Add(new StorylineUpdate
                {
                    StoryId = u.GetValue("storyId", "").AsString,
                    At = u.Contains("at") && u["at"].IsValidDateTime
                        ? new DateTimeOffset(u["at"].ToUniversalTime())
                        : DateTimeOffset.UtcNow,
                    Outlet = u.GetValue("outlet", "").AsString,
                    Summary = u.GetValue("summary", "").AsString,
                    Title = u.GetValue("title", BsonNull.Value).IsBsonNull ? null : u["title"].AsString,
                    AudioStatus = u.GetValue("audioStatus", "pending").AsString,
                    AudioKey = u.GetValue("audioKey", BsonNull.Value).IsBsonNull ? null : u["audioKey"].AsString,
                    ImageUrl = u.GetValue("imageUrl", BsonNull.Value).IsBsonNull ? null : u["imageUrl"].AsString,
                    SourceUrl = u.GetValue("sourceUrl", BsonNull.Value).IsBsonNull ? null : u["sourceUrl"].AsString,
                });
            }
        }

        return new Storyline
        {
            ThreadId = doc.GetValue("threadId").AsString,
            Title = doc.GetValue("title", "").AsString,
            Status = doc.GetValue("status", "open").AsString,
            Topic = doc.GetValue("topic", "Canada").AsString,
            Place = doc.GetValue("place", "Canada").AsString,
            OpenedAt = doc.Contains("openedAt") && doc["openedAt"].IsValidDateTime
                ? new DateTimeOffset(doc["openedAt"].ToUniversalTime())
                : null,
            ClosedAt = doc.Contains("closedAt") && !doc["closedAt"].IsBsonNull && doc["closedAt"].IsValidDateTime
                ? new DateTimeOffset(doc["closedAt"].ToUniversalTime())
                : null,
            UpdatedAt = doc.Contains("updatedAt") && doc["updatedAt"].IsValidDateTime
                ? new DateTimeOffset(doc["updatedAt"].ToUniversalTime())
                : DateTimeOffset.UtcNow,
            Updates = updates,
        };
    }

    private static string EncodeCursor(DateTime updatedAt, string threadId)
    {
        var payload = JsonSerializer.Serialize(new { t = updatedAt.ToUniversalTime(), id = threadId });
        return Convert.ToBase64String(Encoding.UTF8.GetBytes(payload));
    }

    private static bool TryDecodeCursor(string cursor, out DateTime updatedAt, out string threadId)
    {
        updatedAt = default;
        threadId = "";
        try
        {
            var json = Encoding.UTF8.GetString(Convert.FromBase64String(cursor));
            using var doc = JsonDocument.Parse(json);
            updatedAt = doc.RootElement.GetProperty("t").GetDateTime().ToUniversalTime();
            threadId = doc.RootElement.GetProperty("id").GetString() ?? "";
            return !string.IsNullOrWhiteSpace(threadId);
        }
        catch
        {
            return false;
        }
    }
}
