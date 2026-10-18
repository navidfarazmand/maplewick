// Adds Firebase Cloud Messaging (friends' notifications) when mobile/google-services.json is there. Without it the
// app builds and works the same, just without push notifications from friends.
const fs = require('fs');
const path = require('path');

module.exports = ({ config }) => {
  if (fs.existsSync(path.join(__dirname, 'google-services.json'))) {
    config.android = { ...config.android, googleServicesFile: './google-services.json' };
  }
  return config;
};
