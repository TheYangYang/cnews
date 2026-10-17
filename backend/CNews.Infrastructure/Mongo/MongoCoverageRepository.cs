using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using MongoDB.Bson;
using MongoDB.Driver;

namespace CNews.Infrastructure.Mongo;

public sealed class MongoCoverageRepository(IOptions<MongoOptions> options) : ICoverageRepository
{
    private readonly IMongoCollection<BsonDocument> _compares =
        new MongoClient(options.Value.Uri).GetDatabase(options.Value.Database).GetCollection<BsonDocument>("compares");

    public async Task<CoverageCluster?> GetByIdAsync(string clusterId, CancellationToken ct)
    {
        var filter = Builders<BsonDocument>.Filter.Or(
            Builders<BsonDocument>.Filter.Eq("clusterId", clusterId),
            Builders<BsonDocument>.Filter.Eq("clusterId", clusterId.StartsWith("cluster_") ? clusterId : $"cluster_{clusterId}"));
        var doc = await _compares.Find(filter).FirstOrDefaultAsync(ct);
        if (doc is null)
        {
            return null;
        }

        var outlets = new List<CoverageOutlet>();
        if (doc.Contains("outlets") && doc["outlets"].IsBsonArray)
        {
            foreach (var item in doc["outlets"].AsBsonArray)
            {
                var o = item.AsBsonDocument;
                outlets.Add(new CoverageOutlet
                {
                    StoryId = o.GetValue("storyId", "").AsString,
                    Outlet = o.GetValue("outlet", "").AsString,
                    Framing = o.GetValue("framing", "").AsString,
                    Summary = o.GetValue("summary", "").AsString,
                    AudioStatus = o.GetValue("audioStatus", "pending").AsString,
                    AudioKey = o.GetValue("audioKey", BsonNull.Value).IsBsonNull ? null : o["audioKey"].AsString,
                    ImageUrl = o.GetValue("imageUrl", BsonNull.Value).IsBsonNull ? null : o["imageUrl"].AsString,
                    SourceUrl = o.GetValue("sourceUrl", BsonNull.Value).IsBsonNull ? null : o["sourceUrl"].AsString,
                });
            }
        }

        return new CoverageCluster
        {
            ClusterId = doc.GetValue("clusterId").AsString,
            Title = doc.GetValue("title", "").AsString,
            Topics = doc.Contains("topics") && doc["topics"].IsBsonArray
                ? doc["topics"].AsBsonArray.Select(x => x.AsString).ToArray()
                : [],
            UpdatedAt = doc.Contains("updatedAt") && doc["updatedAt"].IsValidDateTime
                ? new DateTimeOffset(doc["updatedAt"].ToUniversalTime())
                : DateTimeOffset.UtcNow,
            Outlets = outlets,
        };
    }
}
