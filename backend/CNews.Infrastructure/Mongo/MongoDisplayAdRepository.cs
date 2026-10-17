using CNews.Application.Abstractions;
using CNews.Domain.Entities;
using Microsoft.Extensions.Options;
using MongoDB.Bson;
using MongoDB.Driver;

namespace CNews.Infrastructure.Mongo;

public sealed class MongoDisplayAdRepository(IOptions<MongoOptions> options) : IDisplayAdRepository
{
    private readonly IMongoCollection<BsonDocument> _ads =
        new MongoClient(options.Value.Uri).GetDatabase(options.Value.Database).GetCollection<BsonDocument>("display_ads");

    public async Task<IReadOnlyList<DisplayAd>> ListActiveAsync(int limit, CancellationToken ct)
    {
        var take = Math.Clamp(limit, 1, 12);
        var docs = await _ads.Find(Builders<BsonDocument>.Filter.Eq("active", true))
            .Limit(take)
            .ToListAsync(ct);
        return docs.Select(Map).ToArray();
    }

    private static DisplayAd Map(BsonDocument doc) => new()
    {
        AdId = doc.GetValue("adId").AsString,
        Advertiser = doc.GetValue("advertiser", "").AsString,
        Title = doc.GetValue("title", "").AsString,
        ClickUrl = doc.GetValue("clickUrl", "").AsString,
        ImageKey = doc.GetValue("imageKey", BsonNull.Value).IsBsonNull ? null : doc["imageKey"].AsString,
        ImageAspect = doc.GetValue("imageAspect", BsonNull.Value).IsBsonNull ? null : doc["imageAspect"].ToDouble(),
        Active = doc.GetValue("active", true).ToBoolean(),
    };
}
