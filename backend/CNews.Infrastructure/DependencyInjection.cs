using CNews.Application.Abstractions;
using CNews.Application.Services;
using CNews.Infrastructure.Auth;
using CNews.Infrastructure.Mongo;
using CNews.Infrastructure.Postgres;
using CNews.Infrastructure.Storage;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace CNews.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddCNewsInfrastructure(this IServiceCollection services, IConfiguration config)
    {
        services.Configure<MongoOptions>(o =>
        {
            o.Uri = config["MONGODB_URI"] ?? config["Mongo:Uri"] ?? o.Uri;
            o.Database = config["MONGODB_DATABASE"] ?? config["Mongo:Database"] ?? o.Database;
        });
        services.Configure<PostgresOptions>(o =>
        {
            o.ConnectionString = config["POSTGRES_CONNECTION"] ?? config["Postgres:ConnectionString"] ?? o.ConnectionString;
        });
        services.Configure<S3Options>(o =>
        {
            o.Bucket = config["S3_BUCKET"] ?? o.Bucket;
            o.Region = config["S3_REGION"] ?? o.Region;
            o.Endpoint = config["S3_ENDPOINT"] ?? o.Endpoint;
            o.AccessKey = config["S3_ACCESS_KEY"] ?? o.AccessKey;
            o.SecretKey = config["S3_SECRET_KEY"] ?? o.SecretKey;
            o.ForcePathStyle = bool.TryParse(config["S3_FORCE_PATH_STYLE"], out var fps) ? fps : o.ForcePathStyle;
            o.UrlTtlSeconds = int.TryParse(config["AUDIO_URL_TTL_SECONDS"], out var ttl) ? ttl : o.UrlTtlSeconds;
            o.PublicBaseUrl = config["PUBLIC_BASE_URL"] ?? config["ASPNETCORE_URLS"]?.Split(';').FirstOrDefault() ?? o.PublicBaseUrl;
        });
        services.Configure<JwtOptions>(o =>
        {
            o.SigningKey = config["JWT_SIGNING_KEY"] ?? o.SigningKey;
            o.Issuer = config["JWT_ISSUER"] ?? o.Issuer;
            o.Audience = config["JWT_AUDIENCE"] ?? o.Audience;
        });
        services.Configure<GoogleAuthOptions>(o =>
        {
            o.ClientIds = config["GOOGLE_CLIENT_IDS"] ?? o.ClientIds;
            o.AllowDevBypass = !string.Equals(config["ASPNETCORE_ENVIRONMENT"], "Production", StringComparison.OrdinalIgnoreCase);
        });

        services.AddSingleton<IStoryRepository, MongoStoryRepository>();
        services.AddSingleton<ICoverageRepository, MongoCoverageRepository>();
        services.AddSingleton<IStorylineRepository, MongoStorylineRepository>();
        services.AddSingleton<IDisplayAdRepository, MongoDisplayAdRepository>();
        services.AddSingleton<IUserRepository, PostgresUserRepository>();
        services.AddSingleton<IAudioUrlService, S3AudioUrlService>();
        services.AddSingleton<IJwtTokenService, JwtTokenService>();
        services.AddSingleton<IGoogleTokenValidator, GoogleTokenValidator>();
        services.AddSingleton<NewsQueryService>();
        services.AddSingleton<DisplayAdService>();
        services.AddSingleton<AuthService>();
        return services;
    }
}
