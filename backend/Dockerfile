FROM public.ecr.aws/lambda/dotnet:10 AS base

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY CNews.slnx ./
COPY CNews.Api/CNews.Api.csproj CNews.Api/
COPY CNews.Application/CNews.Application.csproj CNews.Application/
COPY CNews.Domain/CNews.Domain.csproj CNews.Domain/
COPY CNews.Infrastructure/CNews.Infrastructure.csproj CNews.Infrastructure/
RUN dotnet restore CNews.Api/CNews.Api.csproj
COPY . .
RUN dotnet publish CNews.Api/CNews.Api.csproj -c Release -o /app/publish /p:PublishReadyToRun=true

FROM base AS final
WORKDIR /var/task
COPY --from=build /app/publish .
CMD ["CNews.Api"]
