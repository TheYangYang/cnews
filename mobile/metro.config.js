// Sentry's Metro config adds debug IDs so release crash stack traces map back to source.
const { getSentryExpoConfig } = require('@sentry/react-native/metro');

module.exports = getSentryExpoConfig(__dirname);
