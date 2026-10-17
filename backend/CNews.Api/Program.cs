using System.Text;
using CNews.Api.Endpoints;
using CNews.Infrastructure;
using CNews.Infrastructure.Auth;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.StaticFiles;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Configuration.AddEnvironmentVariables();
builder.WebHost.UseUrls(builder.Configuration["ASPNETCORE_URLS"] ?? "http://0.0.0.0:5080");

builder.Services.AddCNewsInfrastructure(builder.Configuration);
builder.Services.AddAWSLambdaHosting(LambdaEventSource.HttpApi);

var jwtKey = builder.Configuration["JWT_SIGNING_KEY"] ?? "dev-only-change-me-to-a-long-random-secret";
var jwtIssuer = builder.Configuration["JWT_ISSUER"] ?? "cnews";
var jwtAudience = builder.Configuration["JWT_AUDIENCE"] ?? "cnews-mobile";

builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = jwtIssuer,
            ValidAudience = jwtAudience,
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
            NameClaimType = "sub",
        };
    });
builder.Services.AddAuthorization();

builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
        policy.AllowAnyHeader().AllowAnyMethod().AllowAnyOrigin());
});

var app = builder.Build();

app.UseCors();
var contentTypes = new FileExtensionContentTypeProvider();
contentTypes.Mappings[".opus"] = "audio/opus";
contentTypes.Mappings[".m4a"] = "audio/mp4";
app.UseStaticFiles(new StaticFileOptions { ContentTypeProvider = contentTypes });
app.UseAuthentication();
app.UseAuthorization();
app.MapV1();

app.Run();

public partial class Program;
